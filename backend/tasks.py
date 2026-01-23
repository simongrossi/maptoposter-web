import hashlib
import json
import time
import os
import boto3
from typing import Dict, Any
from datetime import datetime
import asyncio
import unicodedata
from io import BytesIO

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.backends.backend_pdf import FigureCanvasPdf
import matplotlib.pyplot as plt

from backend.celery_app import celery_app
from backend.models import PosterRequest
from backend.utils import get_coordinates, load_theme
from backend.fetcher import MapDataFetcher
from backend.renderer import MapRenderer

# S3 Configuration
S3_ENDPOINT = os.getenv("S3_ENDPOINT_URL", "http://minio:9000")
S3_BUCKET = os.getenv("S3_BUCKET", "posters")
S3_PUBLIC_URL = os.getenv("S3_PUBLIC_URL", "http://localhost:9000")
AWS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadminpassword")

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET
    )

@celery_app.task(bind=True)
def generate_poster_task(self, request_data: Dict[str, Any]):
    """
    Celery task to generate a map poster (Stateless/S3).
    """
    try:
        request = PosterRequest(**request_data)
        
        # 1. Check Cache (S3)
        req_dump = request.model_dump_json()
        req_hash = hashlib.md5(req_dump.encode('utf-8')).hexdigest()
        
        def slugify(value):
            value = str(value)
            value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
            value = value.lower().replace(" ", "_")
            return value
            
        safe_city = slugify(request.city)
        filename = f"{safe_city}_{request.style}_{req_hash[:8]}.{request.format.lower()}"
        file_key = f"{filename}" # Key in bucket
        
        s3 = get_s3_client()
        
        try:
            s3.head_object(Bucket=S3_BUCKET, Key=file_key)
            # CACHE HIT
            self.update_state(state='SUCCESS', meta={'current': 100, 'total': 100, 'status': 'Restored from S3 cache'})
            return {
                "success": True, 
                "file_url": f"{S3_PUBLIC_URL}/{S3_BUCKET}/{filename}", 
                "cached": True
            }
        except:
            # Not found, proceed
            pass

        self.update_state(state='PROGRESS', meta={'current': 10, 'total': 100, 'status': 'Decoding parameters...'})

        # Async Logic Wrapper
        async def _async_logic():
            lat, lon = await get_coordinates(request.city, request.country)
            theme = load_theme(request.style)
             
            if request.custom_colors:
                cc = request.custom_colors
                if cc.bg: theme['bg'] = cc.bg
                if cc.water: theme['water'] = cc.water
                if cc.parks: theme['parks'] = cc.parks
                if cc.text: theme['text'] = cc.text
                if cc.roads:
                    for k in list(theme.keys()):
                        if k.startswith('road_'):
                            theme[k] = cc.roads

            aspect = request.width / request.height
            max_dim = max(request.width, request.height)
            min_dim = min(request.width, request.height)
            ratio = max_dim / min_dim
            compensated_dist = request.distance * ratio
            
            data = await MapDataFetcher.fetch_all(lat, lon, compensated_dist, request.custom_layers)
            return lat, lon, theme, data

        self.update_state(state='PROGRESS', meta={'current': 20, 'total': 100, 'status': 'Fetching map data...'})
        
        try:
             lat, lon, theme, data = asyncio.run(_async_logic())
        except Exception:
             lat, lon, theme, data = asyncio.new_event_loop().run_until_complete(_async_logic())

        if not data.get('graph'):
             raise ValueError("Could not retrieve map data for this location.")

        self.update_state(state='PROGRESS', meta={'current': 60, 'total': 100, 'status': 'Rendering map...'})

        # 4. Render
        renderer = MapRenderer(theme)
        fig = renderer.render(
            data=data,
            city=request.city,
            country=request.country,
            point=(lat, lon),
            dist=request.distance,
            width_in=request.width,
            height_in=request.height,
            custom_layers_config=request.custom_layers,
            text_CONFIG={
                'country_label': request.country_label,
                'name_label': request.name_label
            }
        )

        self.update_state(state='PROGRESS', meta={'current': 90, 'total': 100, 'status': 'Uploading to cloud...'})

        # 5. Save to Buffer & Upload
        fmt = request.format.lower()
        if fmt == 'svg':
            canvas = FigureCanvasSVG(fig)
        elif fmt == 'pdf':
            canvas = FigureCanvasPdf(fig)
        else:
            canvas = FigureCanvasAgg(fig)
        
        buf = BytesIO()
        canvas.print_figure(buf, format=fmt, dpi=300, bbox_inches='tight', pad_inches=0.05, facecolor=theme['bg'])
        buf.seek(0)
        
        # Upload
        content_type = f"image/{fmt}" if fmt != 'svg' else 'image/svg+xml'
        if fmt == 'pdf': content_type = 'application/pdf'
        
        s3.upload_fileobj(
            buf, 
            S3_BUCKET, 
            file_key,
            ExtraArgs={'ContentType': content_type}
        )
        
        plt.close(fig)
        buf.close()

        return {
            "success": True, 
            "file_url": f"{S3_PUBLIC_URL}/{S3_BUCKET}/{filename}", 
            "cached": False
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e
