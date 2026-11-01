"""Client Redis partage (broker Celery, quotas, sessions)."""

from __future__ import annotations

import redis

from backend.settings import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """Retourne un client Redis thread-safe (pool de connexions interne)."""
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
            health_check_interval=30,
        )
    return _client


def release_active_slot(
    client: redis.Redis,
    task_id: str,
    session_id: str | None,
    marker_ttl: int = 3600,
) -> None:
    """Libere le compteur de taches actives d'une session, une seule fois.

    Le worker (`task_postrun`) et l'API (statut terminal) peuvent tous les deux
    appeler cette fonction : le marqueur Redis rend l'operation idempotente.
    """
    if not session_id or not task_id:
        return
    try:
        marker = f"slot_released:{task_id}"
        if not client.set(marker, "1", nx=True, ex=marker_ttl):
            return
        key = f"active:{session_id}"
        remaining = client.decr(key)
        if remaining <= 0:
            client.delete(key)
    except Exception:
        # Redis indisponible : le TTL du compteur actif reste le filet de
        # securite. On ne casse jamais la reponse client pour autant.
        return
