"""API FastAPI : dispatch des generations, sessions anonymes, URLs signees.

Principes de securite :
  - aucune origine CORS ouverte : l'API n'est appelee que same-origin via nginx ;
  - chaque navigateur recoit une session anonyme signee (cookie HttpOnly) ;
  - l'enqueue est protege par un quota journalier par IP, un plafond de taches
    actives par session et un plafond de file globale ;
  - les statuts de tache sont invisibles aux autres sessions ;
  - les posters ne sont servis que via une URL HMAC signee et expirante.
"""

from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import logging
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from botocore.exceptions import ClientError
from celery.result import AsyncResult
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware

from backend import storage
from backend.celery_app import celery_app
from backend.models import PosterRequest
from backend.redis_client import get_redis
from backend.security import (
    OBJECT_KEY_RE,
    TASK_ID_RE,
    build_download_url,
    decode_session,
    encode_session,
    new_session_id,
    verify_download,
)
from backend.settings import settings
from backend.utils import list_themes, load_theme

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("maptoposter.api")

# Themes connus, du plus long au plus court, pour reconstituer la ville depuis
# une cle d'objet (format historique : <ville>_<style>_<hash>.<ext>).
_THEME_SUFFIXES = tuple(sorted(list_themes(), key=len, reverse=True))


# ---------------------------------------------------------------------------
# Identification du client (derriere nginx + Caddy)
# ---------------------------------------------------------------------------


def client_ip(request: Request) -> str:
    """IP reelle fournie par notre nginx (X-Real-IP), sinon IP de la socket."""
    raw = (request.headers.get("x-real-ip") or "").strip()
    if raw:
        try:
            return str(ipaddress.ip_address(raw))
        except ValueError:
            pass
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=client_ip)


def _is_https(request: Request) -> bool:
    if settings.cookie_secure == "true":
        return True
    if settings.cookie_secure == "false":
        return False
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "")
    return proto.split(",")[0].strip().lower() == "https"


class SessionMiddleware(BaseHTTPMiddleware):
    """Attribue une session anonyme signee si le navigateur n'en a pas."""

    async def dispatch(self, request: Request, call_next):
        session_id = decode_session(request.cookies.get(settings.cookie_name))
        is_new = session_id is None
        if is_new:
            session_id = new_session_id()

        request.state.session_id = session_id
        response = await call_next(request)

        if is_new:
            response.set_cookie(
                key=settings.cookie_name,
                value=encode_session(session_id),
                max_age=settings.session_ttl,
                httponly=True,
                secure=_is_https(request),
                samesite="lax",
                path="/",
            )

        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response


def _redact_secrets(value: Any) -> str:
    """Empeche un mot de passe Redis de finir dans les logs."""
    text = str(value)
    return re.sub(r"redis://[^@\s]+@", "redis://:***@", text)


def _session_id(request: Request) -> str:
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        # Ne devrait jamais arriver : le middleware est global.
        raise HTTPException(status_code=503, detail="Session unavailable.")
    return session_id


# ---------------------------------------------------------------------------
# Helpers synchrones (executes dans le threadpool)
# ---------------------------------------------------------------------------


def _decrement(client, key: str) -> None:
    try:
        remaining = client.decr(key)
        if remaining <= 0:
            client.delete(key)
    except Exception:
        pass


def _enqueue_poster(body: dict[str, Any], session_id: str, ip: str) -> str:
    """Applique les quotas puis enqueue la tache Celery."""
    try:
        client = get_redis()
    except Exception as exc:  # pragma: no cover - depend de Redis
        raise HTTPException(status_code=503, detail="Queue unavailable.") from exc

    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    quota_key = f"quota:{ip}:{day}"
    active_key = f"active:{session_id}"

    try:
        quota_used = client.incr(quota_key)
        if quota_used == 1:
            client.expire(quota_key, 90000)
        if quota_used > settings.daily_generate_quota:
            raise HTTPException(
                status_code=429,
                detail="Daily generation quota exceeded. Try again tomorrow.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Queue unavailable.") from exc

    try:
        active = client.incr(active_key)
        client.expire(active_key, settings.active_job_ttl)
    except Exception as exc:
        _decrement(client, quota_key)
        raise HTTPException(status_code=503, detail="Queue unavailable.") from exc

    if active > settings.max_active_jobs:
        _decrement(client, active_key)
        _decrement(client, quota_key)
        raise HTTPException(
            status_code=429,
            detail="Too many concurrent generations for this session.",
        )

    try:
        queued = client.llen(settings.queue_name)
    except Exception as exc:
        _decrement(client, active_key)
        _decrement(client, quota_key)
        raise HTTPException(status_code=503, detail="Queue unavailable.") from exc

    if queued >= settings.max_queued_jobs:
        _decrement(client, active_key)
        _decrement(client, quota_key)
        raise HTTPException(
            status_code=503,
            detail="Generation queue is full. Please retry later.",
            headers={"Retry-After": "60"},
        )

    # send_task evite de charger OSMnx/Matplotlib dans le processus API :
    # l'API reste legere et le worker est le seul a importer la tache.
    try:
        task = celery_app.send_task(
            "backend.tasks.generate_poster_task",
            args=[body],
            kwargs={"session_id": session_id},
            queue=settings.queue_name,
        )
    except Exception as exc:
        _decrement(client, active_key)
        _decrement(client, quota_key)
        raise HTTPException(status_code=503, detail="Queue unavailable.") from exc

    try:
        pipe = client.pipeline()
        pipe.set(f"task_owner:{task.id}", session_id, ex=settings.task_ttl)
        pipe.set(f"task_created:{task.id}", int(time.time()), ex=settings.task_ttl)
        pipe.execute()
    except Exception:
        # La tache est deja enqueuee : on ne peut plus l'annuler, mais on
        # journalise pour ne pas renvoyer une fausse impression de succes.
        logger.exception("Impossible d'enregistrer l'ownership de la tache %s", task.id)

    return str(task.id)


def _public_error(info: Any) -> str:
    """Ne jamais renvoyer une trace Python brute au navigateur."""
    text = str(info or "")
    lowered = text.lower()
    if "no map data" in lowered or "could not retrieve map data" in lowered:
        return "No map data found for this area. Try a smaller distance."
    if "time limit" in lowered or "timelimit" in lowered or "soft time" in lowered:
        return "Generation timed out. Try a smaller area or a lower DPI."
    if "nominatim" in lowered or "geocod" in lowered:
        return "Geocoding service temporarily unavailable. Please retry later."
    if "taille maximale" in lowered or "trop elevee" in lowered:
        return "Requested output is too large. Reduce dimensions or DPI."
    return "Poster generation failed."


def _task_status(task_id: str, session_id: str) -> dict[str, Any]:
    try:
        client = get_redis()
        owner = client.get(f"task_owner:{task_id}")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Status unavailable.") from exc

    if owner != session_id:
        # 404 volontaire : ne pas confirmer l'existence d'une tache d'autrui.
        raise HTTPException(status_code=404, detail="Task not found.")

    try:
        result = AsyncResult(task_id, app=celery_app)
        state = result.state
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Status unavailable.") from exc

    response: dict[str, Any] = {
        "task_id": task_id,
        "status": state,
        "result": None,
        "error": None,
    }

    if state in {"PENDING", "STARTED", "RETRY", "PROGRESS"}:
        created_raw = None
        try:
            created_raw = client.get(f"task_created:{task_id}")
        except Exception:
            pass
        if created_raw:
            try:
                if time.time() - int(created_raw) > settings.task_max_age:
                    return {
                        "task_id": task_id,
                        "status": "FAILURE",
                        "result": None,
                        "error": "Generation timed out.",
                    }
            except (TypeError, ValueError):
                pass

        info = result.info if state != "PENDING" else None
        if isinstance(info, dict):
            current = info.get("current", 0)
            total = info.get("total", 100)
            status_text = info.get("status", "Processing...")
        else:
            current, total, status_text = 0, 100, "Pending..."
        response["status"] = "PROGRESS"
        response["progress"] = {
            "current": current,
            "total": total,
            "status": str(status_text)[:200],
        }
        return response

    if state == "SUCCESS":
        value = result.result
        file_key = value.get("file_key") if isinstance(value, dict) else None
        if not isinstance(file_key, str) or not OBJECT_KEY_RE.fullmatch(file_key):
            return {
                "task_id": task_id,
                "status": "FAILURE",
                "result": None,
                "error": "Poster generation failed.",
            }
        response["status"] = "SUCCESS"
        response["result"] = {
            "success": True,
            "file_url": build_download_url(file_key),
            "cached": bool(value.get("cached")) if isinstance(value, dict) else False,
        }
        response["progress"] = {
            "current": 100,
            "total": 100,
            "status": "Completed",
        }
        return response

    if state == "FAILURE":
        response["status"] = "FAILURE"
        response["error"] = _public_error(result.info)
        return response

    response["status"] = "FAILURE"
    response["error"] = "Poster generation failed."
    return response


def _city_from_key(object_key: str) -> str:
    stem = object_key.rsplit(".", 1)[0]
    if "_ALL_THEMES_" in stem:
        city_part = stem.split("_ALL_THEMES_", 1)[0]
    else:
        city_part = re.sub(r"_[0-9a-f]{12}$", "", stem)
        for theme_id in _THEME_SUFFIXES:
            suffix = f"_{theme_id}"
            if city_part.endswith(suffix):
                city_part = city_part[: -len(suffix)]
                break
    return city_part.replace("_", " ").strip().title() or "Map"


def _history(session_id: str, limit: int) -> list[dict[str, Any]]:
    try:
        client = get_redis()
        keys = client.zrevrange(f"session:{session_id}:objects", 0, limit - 1)
    except Exception:
        return []

    history: list[dict[str, Any]] = []
    for key in keys:
        if not isinstance(key, str) or not OBJECT_KEY_RE.fullmatch(key):
            continue
        try:
            head = storage.head_object(key)
        except Exception:
            continue

        modified = head.get("LastModified")
        if isinstance(modified, datetime):
            date_value = modified.astimezone(timezone.utc).isoformat()
        else:
            date_value = ""

        city = _city_from_key(key)

        history.append(
            {
                # Les URLs de l'historique vivent plus longtemps que celles
                # renvoyees immediatement apres la generation.
                "url": build_download_url(key, ttl=max(settings.download_ttl, 3600)),
                "filename": key,
                "date": date_value,
                "city": city,
            }
        )
    return history


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_: FastAPI):
    last_error: Exception | None = None
    for attempt in range(1, 31):
        try:
            await run_in_threadpool(storage.ensure_bucket)
            await run_in_threadpool(get_redis().ping)
            logger.info("Dependances pretes (Redis + stockage S3).")
            break
        except Exception as exc:  # pragma: no cover - depend de l'infra
            last_error = exc
            logger.warning(
                "Dependances indisponibles (tentative %s/30): %s",
                attempt,
                _redact_secrets(exc),
            )
            await asyncio.sleep(2)
    else:
        # Pas de "from last_error" : evite de propager une URL Redis avec mot
        # de passe dans la trace d'un echec de demarrage.
        raise RuntimeError(
            "Redis ou stockage S3 indisponible au demarrage: "
            + _redact_secrets(last_error or "unknown error")
        )

    yield


app = FastAPI(
    title="MapPoster Generator API",
    version="2.3.1",
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
    lifespan=lifespan,
)
app.state.limiter = limiter


async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        {"detail": "Too many requests. Please slow down."},
        status_code=429,
        headers={"Retry-After": "60"},
    )


app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SessionMiddleware)


@app.middleware("http")
async def body_size_guard(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH"}:
        raw_length = request.headers.get("content-length")
        if raw_length and raw_length.isdigit():
            if int(raw_length) > settings.max_request_body_bytes:
                return JSONResponse(
                    {"detail": "Request body too large."}, status_code=413
                )
    return await call_next(request)


# ---------------------------------------------------------------------------
# Sante / readiness
# ---------------------------------------------------------------------------


@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}


@app.get("/ready", include_in_schema=False)
async def ready():
    checks: dict[str, str] = {}
    try:
        await run_in_threadpool(get_redis().ping)
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
    try:
        await run_in_threadpool(storage.check_storage)
        checks["storage"] = "ok"
    except Exception:
        checks["storage"] = "error"
    is_ready = all(value == "ok" for value in checks.values())
    return JSONResponse(
        {"status": "ready" if is_ready else "degraded", "checks": checks},
        status_code=200 if is_ready else 503,
    )


# ---------------------------------------------------------------------------
# Routes metier
# ---------------------------------------------------------------------------


@app.post("/generate")
@limiter.limit(settings.generate_rate_limit)
async def generate_poster_endpoint(request: Request, body: PosterRequest):
    """Enqueue une generation. Retourne {"task_id": "..."}."""
    session_id = _session_id(request)
    task_id = await run_in_threadpool(
        _enqueue_poster,
        body.model_dump(),
        session_id,
        client_ip(request),
    )
    return {"task_id": task_id}


@app.get("/themes")
@limiter.limit("60/minute")
async def get_themes(request: Request):
    """Liste les themes disponibles (lecture seule, sans secret)."""
    themes = []
    for theme_id in list_themes():
        data = load_theme(theme_id)
        themes.append(
            {
                "id": theme_id,
                "name": data.get("name", theme_id),
                "colors": {
                    "bg": data.get("bg"),
                    "road_primary": data.get("road_primary"),
                    "water": data.get("water"),
                },
            }
        )
    return {"themes": themes}


@app.get("/tasks/{task_id}")
@limiter.limit("120/minute")
async def get_task_status(request: Request, task_id: str):
    """Statut d'une tache, reserve a la session qui l'a creee."""
    if not TASK_ID_RE.fullmatch(task_id):
        raise HTTPException(status_code=404, detail="Task not found.")
    session_id = _session_id(request)
    return await run_in_threadpool(_task_status, task_id, session_id)


@app.get("/download/{token}")
@limiter.limit("120/minute")
async def download_result(
    request: Request,
    token: str,
    expires: Optional[str] = None,
    signature: Optional[str] = None,
):
    """Sert un poster via une URL signee, ou redirige l'ancienne route tache."""
    session_id = _session_id(request)

    # Ancienne route /download/{task_id} : conservee pour compatibilite, mais
    # desormais protegee par l'ownership de la tache.
    if expires is None and signature is None:
        if not TASK_ID_RE.fullmatch(token):
            raise HTTPException(status_code=403, detail="Invalid or expired link.")
        return await _legacy_task_download(token, session_id)

    if not OBJECT_KEY_RE.fullmatch(token):
        raise HTTPException(status_code=404, detail="Not found.")
    if expires is None or signature is None:
        raise HTTPException(status_code=403, detail="Invalid or expired link.")

    try:
        expires_at = int(expires)
    except (TypeError, ValueError):
        raise HTTPException(status_code=403, detail="Invalid or expired link.")

    if not verify_download(token, expires_at, signature):
        raise HTTPException(status_code=403, detail="Invalid or expired link.")

    try:
        body, response = await run_in_threadpool(storage.stream_object, token)
    except ClientError:
        raise HTTPException(status_code=404, detail="Not found.")
    except Exception as exc:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]
        logger.warning("Lecture S3 impossible (hash=%s): %s", token_hash, exc)
        raise HTTPException(status_code=502, detail="Storage unavailable.")

    content_type = _content_type_for(token)
    extension = token.rsplit(".", 1)[-1].lower()
    disposition = "attachment" if extension == "zip" else "inline"

    headers = {
        "Content-Disposition": f'{disposition}; filename="{token}"',
        "Cache-Control": "private, max-age=300",
        "X-Content-Type-Options": "nosniff",
    }
    content_length = response.get("ContentLength")
    if content_length is not None:
        headers["Content-Length"] = str(content_length)
    if extension == "svg":
        # Empeche l'execution d'un eventuel script si le SVG est ouvert
        # directement dans le navigateur (defense en profondeur).
        headers["Content-Security-Policy"] = "default-src 'none'; sandbox"

    return StreamingResponse(
        storage.iter_body(body),
        media_type=content_type,
        headers=headers,
    )


async def _legacy_task_download(task_id: str, session_id: str):
    try:
        client = get_redis()
        owner = client.get(f"task_owner:{task_id}")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Status unavailable.") from exc

    if owner != session_id:
        raise HTTPException(status_code=404, detail="Task not found.")

    result = AsyncResult(task_id, app=celery_app)
    if result.state != "SUCCESS":
        raise HTTPException(status_code=404, detail="Result not ready or not found.")

    value = result.result
    file_key = value.get("file_key") if isinstance(value, dict) else None
    if not isinstance(file_key, str) or not OBJECT_KEY_RE.fullmatch(file_key):
        raise HTTPException(status_code=404, detail="Result not ready or not found.")

    return RedirectResponse(build_download_url(file_key), status_code=307)


@app.get("/history")
@limiter.limit("30/minute")
async def get_history(request: Request, limit: int = 10):
    """Historique des affiches de la session courante (jamais global)."""
    session_id = _session_id(request)
    safe_limit = max(1, min(int(limit), 50))
    return await run_in_threadpool(_history, session_id, safe_limit)


@app.get("/geocode")
@limiter.limit("10/minute")
async def geocode_proxy(request: Request, q: str):
    """Proxy Nominatim borne, pour eviter les abus et les blocages CORS."""
    query = q.strip()
    if not query or len(query) > 200:
        raise HTTPException(status_code=422, detail="Invalid query.")

    params = {
        "format": "jsonv2",
        "q": query,
        "limit": 1,
        "addressdetails": 0,
    }
    headers = {
        "User-Agent": settings.nominatim_user_agent,
        "Accept-Language": "fr",
    }

    try:
        async with httpx.AsyncClient(
            timeout=settings.geocode_timeout, headers=headers
        ) as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search", params=params
            )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Geocoding timeout.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Geocoding unavailable.") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Geocoding unavailable.")

    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Geocoding unavailable.") from exc


def _content_type_for(object_key: str) -> str:
    extension = object_key.rsplit(".", 1)[-1].lower()
    return {
        "png": "image/png",
        "svg": "image/svg+xml",
        "pdf": "application/pdf",
        "zip": "application/zip",
    }.get(extension, "application/octet-stream")
