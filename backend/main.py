from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from celery.result import AsyncResult
from typing import Dict, Any

from backend.models import PosterRequest
from backend.tasks import generate_poster_task

app = FastAPI(title="MapPoster Generator API (Async)")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/generate")
async def generate_poster_endpoint(request: PosterRequest):
    """
    Enqueue a poster generation task.
    Returns: {"task_id": "..."}
    """
    # Convert model to dict for Celery
    task = generate_poster_task.delay(request.model_dump())
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

# Legacy Stream Endpoint (Removed/Deprecated)
# The frontend must migrate to polling /tasks/{id}
