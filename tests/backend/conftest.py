"""Fixtures de test : environnement isole, faux Redis, fausse tache Celery."""

import os
from typing import Any
from unittest.mock import MagicMock

# L'application exige des secrets : on fournit des valeurs de test avant tout
# import de backend.*. Aucune de ces valeurs n'est un secret de production.
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("S3_ENDPOINT_URL", "http://localhost:9000")
os.environ.setdefault("S3_BUCKET", "posters-test")
os.environ.setdefault("S3_ACCESS_KEY", "test-access-key")
os.environ.setdefault("S3_SECRET_KEY", "test-secret-key")
os.environ.setdefault("SESSION_SECRET", "s" * 64)
os.environ.setdefault("DOWNLOAD_SIGNING_SECRET", "d" * 64)
os.environ.setdefault("GENERATE_RATE_LIMIT", "1000/minute")
os.environ.setdefault("DAILY_GENERATE_QUOTA", "1000")
os.environ.setdefault("ENABLE_DOCS", "false")

import pytest
from fastapi.testclient import TestClient


class FakePipeline:
    def __init__(self, redis: "FakeRedis"):
        self.redis = redis
        self.commands: list[tuple[str, tuple, dict]] = []

    def set(self, key: str, value: Any, ex: int | None = None):
        self.commands.append(("set", (key, value), {"ex": ex}))
        return self

    def zadd(self, key: str, mapping: dict):
        self.commands.append(("zadd", (key, mapping), {}))
        return self

    def zremrangebyrank(self, key: str, start: int, end: int):
        self.commands.append(("zremrangebyrank", (key, start, end), {}))
        return self

    def expire(self, key: str, ttl: int):
        self.commands.append(("expire", (key, ttl), {}))
        return self

    def execute(self):
        results = []
        for name, args, kwargs in self.commands:
            results.append(getattr(self.redis, name)(*args, **kwargs))
        self.commands.clear()
        return results


class FakeRedis:
    """Implementation minimale des commandes utilisees par l'API."""

    def __init__(self):
        self.values: dict[str, Any] = {}
        self.zsets: dict[str, dict[str, float]] = {}

    def ping(self):
        return True

    def incr(self, key: str) -> int:
        value = int(self.values.get(key, 0)) + 1
        self.values[key] = value
        return value

    def decr(self, key: str) -> int:
        value = int(self.values.get(key, 0)) - 1
        if value <= 0:
            self.values.pop(key, None)
            return 0
        self.values[key] = value
        return value

    def delete(self, key: str):
        self.values.pop(key, None)
        self.zsets.pop(key, None)
        return 1

    def expire(self, key: str, ttl: int, nx: bool = False):
        return True

    def set(self, key: str, value: Any, ex: int | None = None, nx: bool = False):
        if nx and key in self.values:
            return None
        self.values[key] = value
        return True

    def get(self, key: str):
        return self.values.get(key)

    def llen(self, key: str) -> int:
        return 0

    def zadd(self, key: str, mapping: dict):
        bucket = self.zsets.setdefault(key, {})
        bucket.update(mapping)
        return len(mapping)

    def zremrangebyrank(self, key: str, start: int, end: int):
        bucket = self.zsets.get(key, {})
        ordered = sorted(bucket.items(), key=lambda item: item[1], reverse=True)
        for member, _ in ordered[start : end + 1]:
            bucket.pop(member, None)
        return 0

    def zrevrange(self, key: str, start: int, end: int):
        bucket = self.zsets.get(key, {})
        ordered = sorted(bucket.items(), key=lambda item: item[1], reverse=True)
        return [member for member, _ in ordered[start : end + 1]]

    def pipeline(self):
        return FakePipeline(self)


from backend.main import app  # noqa: E402

TASK_ID = "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture(autouse=True)
def fake_redis(mocker):
    fake = FakeRedis()
    mocker.patch("backend.main.get_redis", return_value=fake)
    return fake


@pytest.fixture(autouse=True)
def fake_send_task(mocker):
    """Evite tout acces reseau a Redis/Celery lors des tests d'API."""
    result = MagicMock()
    result.id = TASK_ID
    return mocker.patch("backend.main.celery_app.send_task", return_value=result)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_celery_task(fake_send_task):
    return fake_send_task
