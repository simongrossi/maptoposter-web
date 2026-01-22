from fastapi import FastAPI, HTTPException
import uvicorn
import asyncio
from pathlib import Path
from datetime import datetime
from matplotlib.backends.backend_agg import FigureCanvasAgg

from backend.models import PosterRequest
from backend.utils import get_coordinates, load_theme, load_fonts
from backend.fetcher import MapDataFetcher
from backend.renderer import MapRenderer

app = FastAPI(title="MapPoster Generator API")

POSTERS_DIR = Path("static/posters")
POSTERS_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/generate")
async def generate_poster(request: PosterRequest):
    try:
        # 1. Resolve Coordinates
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
                # Apply unified road color to all types
                for k in list(theme.keys()):
                    if k.startswith('road_'):
                        theme[k] = cc.roads
        
        # 3. Fetch Data
        # Compensate distance for aspect ratio cropping
        # Logic: fetch enough area to cover the larger dimension
        aspect = request.width / request.height
        max_dim = max(request.width, request.height)
        min_dim = min(request.width, request.height)
        ratio = max_dim / min_dim
        compensated_dist = request.distance * ratio
        
        # Parallel fetch
        data = await MapDataFetcher.fetch_all(lat, lon, compensated_dist, request.custom_layers)
        
        if not data.get('graph'):
            raise HTTPException(status_code=404, detail="Could not retrieve map data for this location.")

        # 4. Render
        # Run rendering in thread pool to avoid blocking event loop (Matplotlib is CPU bound)
        def _render():
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
            return fig

        fig = await asyncio.to_thread(_render)

        # 5. Save
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_city = request.city.lower().replace(" ", "_")
        filename = f"{safe_city}_{request.style}_{timestamp}.{request.format.lower()}"
        output_path = POSTERS_DIR / filename
        
        def _save():
            canvas = FigureCanvasAgg(fig)
            # dpi=300 for high quality
            canvas.print_figure(str(output_path), dpi=300, bbox_inches='tight', pad_inches=0.05, facecolor=theme['bg'])
            # Clean up memory
            import matplotlib.pyplot as plt
            plt.close(fig) 
            # Note: since we used Figure() directly, plt.close(fig) might check global state manager, 
            # but explicit del or clear is good. Figure objects don't register to pyplot unless asked.
            # Using FigureCanvasAgg print_figure is safe.

        await asyncio.to_thread(_save)
        
        return {
            "success": True, 
            "file_url": f"/posters/{filename}", 
            "file_path": str(output_path)
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
