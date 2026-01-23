from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from celery.result import AsyncResult
from typing import Dict, Any

from backend.models import PosterRequest
from backend.tasks import generate_poster_task

import os
import sentry_sdk
from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Sentry Init
if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="MapPoster Generator API (Async)")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/generate")
@limiter.limit("5/minute")
async def generate_poster_endpoint(request: Request, body: PosterRequest):
    """
    Enqueue a poster generation task.
    Returns: {"task_id": "..."}
    """
    # Convert model to dict for Celery
    task = generate_poster_task.delay(body.model_dump())
    return {"task_id": task.id}

@app.get("/themes")
async def get_themes():
    """
    List available themes.
    """
    # This logic was in fetcher/utils or similar.
    # Simple reimplementation or import
    from pathlib import Path
    import json
    
    themes = []
    themes_dir = Path("themes")
    if themes_dir.exists():
        for f in themes_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding='utf-8'))
                themes.append({
                    "id": f.stem,
                    "name": data.get("name", f.stem),
                    "colors": {
                        "bg": data.get("bg"),
                        "road_primary": data.get("road_primary"),
                        "water": data.get("water")
                    }
                })
            except:
                pass
    return {"themes": themes}

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    Get the status of a generation task.
    """
    task_result = AsyncResult(task_id)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
        "result": None,
        "error": None
    }

    if task_result.state == 'PENDING':
        response["status"] = "PENDING"
        response["progress"] = {"current": 0, "total": 100, "status": "Pending..."}
        
    elif task_result.state == 'PROGRESS':
        response["status"] = "PROGRESS"
        response["progress"] = task_result.info # Contains 'current', 'total', 'status'
        
    elif task_result.state == 'SUCCESS':
        response["status"] = "SUCCESS"
        response["result"] = task_result.result
        response["progress"] = {"current": 100, "total": 100, "status": "Completed"}
        
    elif task_result.state == 'FAILURE':
        response["status"] = "FAILURE"
        response["error"] = str(task_result.info)
        
    return response

@app.get("/download/{task_id}")
async def download_task_result(task_id: str):
    """
    Redirect to the generated file URL (S3).
    """
    res = AsyncResult(task_id)
    if res.state == 'SUCCESS':
         url = res.result.get('file_url')
         if url:
             from fastapi.responses import RedirectResponse
             return RedirectResponse(url)
    
    raise HTTPException(status_code=404, detail="Result not ready or not found")

# Legacy Stream Endpoint (Removed/Deprecated)
# The frontend must migrate to polling /tasks/{id}

import httpx

@app.get("/geocode")
async def geocode_proxy(q: str):
    """
    Proxy to Nominatim to bypass CORS/User-Agent browser restrictions.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "format": "json",
        "q": q,
        "limit": 1
    }
    headers = {
        "User-Agent": "MapPoster/2.0 (Backend Proxy)"
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Nominatim error")
        return resp.json()
@app.get("/history")
async def get_history(request: Request, limit: int = 10):
    """
    List recent generated posters from S3.
    """
    from backend.tasks import get_s3_client, build_public_url, S3_BUCKET
    s3 = get_s3_client()
    base_url = S3_PUBLIC_URL.rstrip("/")
    if base_url.startswith("/"):
        base_url = f"{str(request.base_url).rstrip('/')}{base_url}"
    elif base_url.startswith(("http://localhost", "https://localhost", "http://127.0.0.1", "https://127.0.0.1")):
        base_url = f"{str(request.base_url).rstrip('/')}/minio_storage"
    
    try:
        # List objects
        resp = s3.list_objects_v2(Bucket=S3_BUCKET)
        if 'Contents' not in resp:
            return []
            
        # Sort by LastModified desc
        objects = sorted(resp['Contents'], key=lambda x: x['LastModified'], reverse=True)
        
        history = []
        for obj in objects[:limit]:
            key = obj['Key']
            # Parse metadata from filename if possible or just return key
            # Filename format: city_theme_hash.ext
            parts = key.rsplit('.', 1)[0].split('_')
            
            # Simple heuristic
            city = parts[0] if len(parts) > 0 else "Unknown"
            
            history.append({
                "url": f"{base_url}/{S3_BUCKET}/{key}",
                "filename": key,
                "date": obj['LastModified'].isoformat(),
                "city": city.replace("-", " ").title()
            })
            
        return history
    except Exception as e:
        print(f"History error: {e}")
        return []
