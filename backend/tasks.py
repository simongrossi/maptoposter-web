import hashlib
import json
import glob
import time
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta
import asyncio
import unicodedata

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_svg import FigureCanvasSVG
from matplotlib.backends.backend_pdf import FigureCanvasPdf
import matplotlib.pyplot as plt

from backend.celery_app import celery_app
from backend.models import PosterRequest
from backend.utils import get_coordinates, load_theme, load_fonts
from backend.fetcher import MapDataFetcher
from backend.renderer import MapRenderer

POSTERS_DIR = Path("static/posters")
POSTERS_DIR.mkdir(parents=True, exist_ok=True)

def cleanup_old_posters(max_age_hours=24):
    """Delete posters older than max_age_hours."""
    try:
        cutoff = time.time() - (max_age_hours * 3600)
        for f in POSTERS_DIR.glob("*"):
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink()
    except Exception as e:
        print(f"Cleanup error: {e}")

@celery_app.task(bind=True)
def generate_poster_task(self, request_data: Dict[str, Any]):
    """
    Celery task to generate a map poster.
    """
    try:
        # 1. Cleanup old files first (simple periodic maintenance)
        # Running it here avoids needing a separate beat scheduler for now.
        if datetime.now().minute % 30 == 0: # Run roughly every 30 mins logic if many tasks
             cleanup_old_posters()
        else:
             # Or just run it always? It is fast on small folders.
             cleanup_old_posters()

        request = PosterRequest(**request_data)
        
        # 2. Check Cache (Hash-based)
        # We need to resolve lat/lon FIRST to include them in hash? 
        # Or hash the request parameters (city, country, style, layers...) ?
        # City/Country strings map to lat/lon. If OSM result changes, it's ok to regenerate eventually, 
        # but for caching SAME request, we stick to inputs.
        
        # Generate stable hash
        req_dump = request.model_dump_json()
        req_hash = hashlib.md5(req_dump.encode('utf-8')).hexdigest()
        
        # Filename format: {sanitized_city}_{style}_{hash}.{ext}
        # Sanitize city
        def slugify(value):
            value = str(value)
            value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
            value = value.lower().replace(" ", "_")
            return value
            
        safe_city = slugify(request.city)
        filename = f"{safe_city}_{request.style}_{req_hash[:8]}.{request.format.lower()}"
        output_path = POSTERS_DIR / filename
        
        if output_path.exists():
            # CACHE HIT!
            self.update_state(state='SUCCESS', meta={'current': 100, 'total': 100, 'status': 'Restored from cache'})
            return {
                "success": True, 
                "file_url": f"/posters/{filename}", 
                "file_path": str(output_path),
                "cached": True
            }

        # CACHE MISS - Proceed to generation
        self.update_state(state='PROGRESS', meta={'current': 10, 'total': 100, 'status': 'Decoding parameters...'})

        async def _async_logic():
            # 1. Resolve
            lat, lon = await get_coordinates(request.city, request.country)
            
            # 2. Config & Theme
            theme = load_theme(request.style)
             
            # Apply color overrides
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

            # 3. Fetch Data
            aspect = request.width / request.height
            max_dim = max(request.width, request.height)
            min_dim = min(request.width, request.height)
            ratio = max_dim / min_dim
            compensated_dist = request.distance * ratio
            
            data = await MapDataFetcher.fetch_all(lat, lon, compensated_dist, request.custom_layers)
            return lat, lon, theme, data

        self.update_state(state='PROGRESS', meta={'current': 20, 'total': 100, 'status': 'Fetching map data...'})
        
        # Run async part
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

        self.update_state(state='PROGRESS', meta={'current': 90, 'total': 100, 'status': 'Saving file...'})

        # 5. Save
        fmt = request.format.lower()
        if fmt == 'svg':
            canvas = FigureCanvasSVG(fig)
        elif fmt == 'pdf':
            canvas = FigureCanvasPdf(fig)
        else:
            canvas = FigureCanvasAgg(fig)
        
        canvas.print_figure(str(output_path), dpi=300, bbox_inches='tight', pad_inches=0.05, facecolor=theme['bg'])
        
        # Cleanup Memory
        plt.close(fig)

        return {
            "success": True, 
            "file_url": f"/posters/{filename}", 
            "file_path": str(output_path),
            "cached": False
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e
