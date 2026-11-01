"""Tache Celery de generation des affiches.

Le worker est volontairement borne :
  - concurrence 1 et un processus enfant par tache (voir docker-compose.yml) ;
  - plafond memoire Docker (2 Go) + recyclage Celery ;
  - duree maximale soft/hard ;
  - une seule tache lourde en memoire a la fois.
"""

from __future__ import annotations

import asyncio
import gc
import hashlib
import logging
import time
import unicodedata
import zipfile
from io import BytesIO
from typing import Any, Dict, Optional

from celery.signals import task_postrun

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_pdf import FigureCanvasPdf
from matplotlib.backends.backend_svg import FigureCanvasSVG

from backend import storage
from backend.celery_app import celery_app
from backend.fetcher import MapDataFetcher
from backend.models import PosterRequest
from backend.redis_client import get_redis
from backend.renderer import MapRenderer
from backend.settings import settings
from backend.utils import get_coordinates, list_themes, load_theme, safe_slug

logger = logging.getLogger(__name__)

_CONTENT_TYPES = {
    "png": "image/png",
    "svg": "image/svg+xml",
    "pdf": "application/pdf",
    "zip": "application/zip",
}


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _request_hash(request: PosterRequest) -> str:
    return hashlib.sha256(request.model_dump_json().encode("utf-8")).hexdigest()


def _build_file_key(request: PosterRequest, request_hash: str) -> str:
    city = safe_slug(request.city)
    if request.all_themes:
        return f"{city}_ALL_THEMES_{request_hash[:12]}.zip"
    style = safe_slug(request.style, fallback="theme")
    return f"{city}_{style}_{request_hash[:12]}.{request.format}"


def _record_object(session_id: Optional[str], object_key: str) -> None:
    """Indexe l'objet pour l'historique de la session (borne et expire)."""
    if not session_id:
        return
    try:
        client = get_redis()
        redis_key = f"session:{session_id}:objects"
        pipe = client.pipeline()
        pipe.zadd(redis_key, {object_key: time.time()})
        pipe.zremrangebyrank(redis_key, 0, -51)
        pipe.expire(redis_key, settings.session_ttl)
        pipe.execute()
    except Exception as exc:  # pragma: no cover - depend de Redis
        logger.warning("Indexation de l'historique impossible: %s", exc)


def _maybe_cleanup_storage() -> None:
    """Nettoyage opportuniste, au plus une fois par heure."""
    if settings.poster_retention_days <= 0 and settings.max_stored_posters <= 0:
        return
    try:
        client = get_redis()
        if not client.set("storage:cleanup:lock", "1", nx=True, ex=3600):
            return
    except Exception:
        return

    try:
        storage.cleanup_old_objects(
            settings.poster_retention_days, settings.max_stored_posters
        )
    except Exception as exc:  # pragma: no cover - depend du backend
        logger.warning("Nettoyage du stockage en echec: %s", exc)


def _canvas_for(fmt: str, figure):
    if fmt == "svg":
        return FigureCanvasSVG(figure)
    if fmt == "pdf":
        return FigureCanvasPdf(figure)
    return FigureCanvasAgg(figure)


def _render_to_bytes(
    theme: Dict[str, Any],
    data: Dict[str, Any],
    request: PosterRequest,
    point: tuple,
) -> bytes:
    renderer = MapRenderer(theme)
    figure = renderer.render(
        data=data,
        city=request.city,
        country=request.country,
        point=point,
        dist=request.distance,
        width_in=request.width,
        height_in=request.height,
        custom_layers_config=request.custom_layers,
        text_CONFIG={
            "country_label": request.country_label,
            "name_label": request.name_label,
        },
        margins=request.margins,
    )

    buffer = BytesIO()
    try:
        canvas = _canvas_for(request.format, figure)
        canvas.print_figure(
            buffer,
            format=request.format,
            dpi=request.dpi,
            facecolor=theme.get("bg", "#FFFFFF"),
        )
        return buffer.getvalue()
    finally:
        buffer.close()
        try:
            figure.clear()
        except Exception:
            pass
        del figure


@celery_app.task(
    bind=True,
    name="backend.tasks.generate_poster_task",
    soft_time_limit=settings.task_soft_timeout,
    time_limit=settings.task_hard_timeout,
)
def generate_poster_task(
    self,
    request_data: Dict[str, Any],
    session_id: Optional[str] = None,
):
    """Genere une affiche (ou un ZIP multi-themes) et la stocke dans S3."""
    started_at = time.monotonic()
    request = PosterRequest(**request_data)
    storage.ensure_bucket()

    request_hash = _request_hash(request)
    file_key = _build_file_key(request, request_hash)

    # ------------------------------------------------------------------
    # 1. Cache S3
    # ------------------------------------------------------------------
    if storage.object_exists(file_key):
        _record_object(session_id, file_key)
        logger.info("Cache hit (hash=%s)", request_hash[:12])
        return {"success": True, "file_key": file_key, "cached": True}

    try:
        if request.all_themes:
            # ----------------------------------------------------------
            # 2a. Mode multi-themes : un seul telechargement OSM
            # ----------------------------------------------------------
            themes_to_render = list_themes() or [request.style]
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": 15,
                    "total": 100,
                    "status": f"Preparing {len(themes_to_render)} themes...",
                },
            )

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": 20,
                    "total": 100,
                    "status": "Downloading OSM road network...",
                },
            )

            def _graph_ready():
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": 40,
                        "total": 100,
                        "status": "Downloading water and parks...",
                    },
                )

            async def _fetch_once():
                lat, lon = await get_coordinates(request.city, request.country)
                # Le renderer recadre toujours dans un carre de rayon
                # `distance` : inutile de sur-telecharger selon le ratio.
                data = await MapDataFetcher.fetch_all(
                    lat,
                    lon,
                    request.distance,
                    request.custom_layers,
                    on_graph_ready=_graph_ready,
                )
                return lat, lon, data

            lat, lon, data = _run_async(_fetch_once())
            if not data.get("graph"):
                raise ValueError("No map data found.")

            zip_buffer = BytesIO()
            total_bytes = 0
            try:
                with zipfile.ZipFile(
                    zip_buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=6
                ) as archive:
                    total_themes = len(themes_to_render)
                    for index, theme_id in enumerate(themes_to_render):
                        percent = 50 + int((index / total_themes) * 40)
                        self.update_state(
                            state="PROGRESS",
                            meta={
                                "current": percent,
                                "total": 100,
                                "status": (
                                    f"Rendering {theme_id} "
                                    f"({index + 1}/{total_themes})..."
                                ),
                            },
                        )
                        theme_config = load_theme(theme_id)
                        payload = _render_to_bytes(
                            theme_config, data, request, (lat, lon)
                        )
                        total_bytes += len(payload)
                        if total_bytes > settings.max_archive_bytes:
                            raise ValueError(
                                "L'archive demandee depasse la taille maximale autorisee."
                            )
                        archive.writestr(
                            f"{safe_slug(request.city)}_{theme_id}.{request.format}",
                            payload,
                        )
                        del payload

                zip_buffer.seek(0)
                storage.upload_fileobj(
                    zip_buffer,
                    file_key,
                    _CONTENT_TYPES["zip"],
                )
            finally:
                zip_buffer.close()

        else:
            # ----------------------------------------------------------
            # 2b. Mode mono-theme
            # ----------------------------------------------------------
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": 10,
                    "total": 100,
                    "status": "Decoding parameters...",
                },
            )

            def _graph_ready():
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": 40,
                        "total": 100,
                        "status": "Downloading water and parks...",
                    },
                )

            async def _render_once():
                lat, lon = await get_coordinates(request.city, request.country)
                theme = load_theme(request.style)

                if request.custom_colors:
                    colors = request.custom_colors
                    if colors.bg:
                        theme["bg"] = colors.bg
                    if colors.water:
                        theme["water"] = colors.water
                    if colors.parks:
                        theme["parks"] = colors.parks
                    if colors.text:
                        theme["text"] = colors.text
                    if colors.roads:
                        for key in list(theme.keys()):
                            if key.startswith("road_"):
                                theme[key] = colors.roads

                data = await MapDataFetcher.fetch_all(
                    lat,
                    lon,
                    request.distance,
                    request.custom_layers,
                    on_graph_ready=_graph_ready,
                )
                return lat, lon, theme, data

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": 20,
                    "total": 100,
                    "status": "Downloading OSM road network...",
                },
            )
            lat, lon, theme, data = _run_async(_render_once())

            if not data.get("graph"):
                raise ValueError("Could not retrieve map data for this location.")

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": 60,
                    "total": 100,
                    "status": "Rendering map...",
                },
            )
            payload = _render_to_bytes(theme, data, request, (lat, lon))
            if len(payload) > settings.max_archive_bytes:
                raise ValueError("Le fichier demande depasse la taille maximale autorisee.")

            self.update_state(
                state="PROGRESS",
                meta={
                    "current": 90,
                    "total": 100,
                    "status": "Uploading to cloud...",
                },
            )
            with BytesIO(payload) as upload_buffer:
                storage.upload_fileobj(
                    upload_buffer, file_key, _CONTENT_TYPES[request.format]
                )

        _record_object(session_id, file_key)
        logger.info(
            "Affiche generee (hash=%s, %.1fs)",
            request_hash[:12],
            time.monotonic() - started_at,
        )
        return {"success": True, "file_key": file_key, "cached": False}

    except Exception:
        logger.exception("Echec de generation (hash=%s)", request_hash[:12])
        raise

    finally:
        # Libere les graphes/geometries avant le prochain task du worker.
        data = None
        theme = None
        gc.collect()
        _maybe_cleanup_storage()


@task_postrun.connect
def _release_active_slot(
    task_id=None,
    task=None,
    args=None,
    kwargs=None,
    retval=None,
    state=None,
    **extra,
):
    """Libere le compteur de taches actives de la session, meme en cas d'echec."""
    session_id = (kwargs or {}).get("session_id")
    if not session_id:
        return
    try:
        client = get_redis()
        key = f"active:{session_id}"
        remaining = client.decr(key)
        if remaining <= 0:
            client.delete(key)
    except Exception as exc:  # pragma: no cover - depend de Redis
        logger.warning("Liberation du slot de session impossible: %s", exc)
