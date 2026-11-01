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
