"""Configuration Celery partagee API/worker."""

from __future__ import annotations

import sentry_sdk
from celery import Celery

from backend.settings import settings


def _scrub_sentry_event(event, _hint=None):
    """Retire les query strings (signatures d'URLs) des evenements Sentry."""
    request = event.get("request") if isinstance(event, dict) else None
    if isinstance(request, dict):
        request.pop("query_string", None)
        url = request.get("url")
        if isinstance(url, str) and "?" in url:
            request["url"] = url.split("?", 1)[0]
    return event


if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        profiles_sample_rate=0.0,
        send_default_pii=False,
        environment=settings.environment,
        max_request_body_size="never",
        before_send=_scrub_sentry_event,
        before_send_transaction=_scrub_sentry_event,
    )

celery_app = Celery(
    "maptoposter",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["backend.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.timezone,
    enable_utc=True,
    task_track_started=True,
    task_ignore_result=False,
    result_expires=settings.result_ttl,
    task_soft_time_limit=settings.task_soft_timeout,
    task_time_limit=settings.task_hard_timeout,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1,
    worker_max_memory_per_child=settings.worker_max_memory_kb,
    worker_send_task_events=False,
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": settings.task_hard_timeout + 300,
    },
    task_default_queue=settings.queue_name,
)

# Le worker ne doit pas charger le result backend pour chaque tache si cela
# n'est pas necessaire ; les statuts sont lus par l'API via AsyncResult.
celery_app.conf.task_acks_late = False
celery_app.conf.task_reject_on_worker_lost = False
