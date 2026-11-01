"""Configuration centralisee de l'API et du worker.

Toutes les valeurs sensibles sont lues dans l'environnement. Aucun secret
n'a de valeur par defaut : l'application refuse de demarrer si une variable
obligatoire manque, afin d'eviter un deploiement silencieusement insecure.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass


class ConfigError(RuntimeError):
    """Erreur de configuration bloquante au demarrage."""


def _raw(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _required(name: str, *, min_length: int = 1) -> str:
    value = _raw(name)
    if value is None:
        raise ConfigError(
            f"{name} est obligatoire. Renseignez-le dans .env "
            "(voir .env.example) avant de demarrer le service."
        )
    if len(value) < min_length:
        raise ConfigError(
            f"{name} doit contenir au moins {min_length} caracteres "
            f"({len(value)} recus)."
        )
    return value


def _optional(name: str, default: str) -> str:
    return _raw(name) or default


def _integer(
    name: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    raw = _raw(name)
    if raw is None:
        value = default
    else:
        try:
            value = int(raw)
        except ValueError as exc:
            raise ConfigError(f"{name} doit etre un entier (recu: {raw!r}).") from exc
    if minimum is not None and value < minimum:
        raise ConfigError(f"{name} doit etre >= {minimum} (recu: {value}).")
    if maximum is not None and value > maximum:
        raise ConfigError(f"{name} doit etre <= {maximum} (recu: {value}).")
    return value


def _float(
    name: str,
    default: float,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    raw = _raw(name)
    if raw is None:
        value = default
    else:
        try:
            value = float(raw)
        except ValueError as exc:
            raise ConfigError(f"{name} doit etre un nombre (recu: {raw!r}).") from exc
    if minimum is not None and value < minimum:
        raise ConfigError(f"{name} doit etre >= {minimum} (recu: {value}).")
    if maximum is not None and value > maximum:
        raise ConfigError(f"{name} doit etre <= {maximum} (recu: {value}).")
    return value


def _boolean(name: str, default: bool) -> bool:
    raw = _raw(name)
    if raw is None:
        return default
    lowered = raw.lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{name} doit etre un booleen (recu: {raw!r}).")


_BUCKET_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")


@dataclass(frozen=True)
class Settings:
    # Infrastructure
    redis_url: str
    s3_endpoint_url: str
    s3_bucket: str
    s3_region: str
    s3_access_key: str
    s3_secret_key: str

    # Secrets applicatifs
    session_secret: str
    download_signing_secret: str

    # Sessions / URLs
    cookie_name: str
    cookie_secure: str
    session_ttl: int
    download_ttl: int
    public_base_url: str

    # Quotas
    generate_rate_limit: str
    daily_generate_quota: int
    max_active_jobs: int
    max_queued_jobs: int
    queue_name: str

    # Plafonds de rendu
    max_distance_m: int
    max_output_pixels: int
    max_dimension_inches: int
    max_dpi: int
    max_request_body_bytes: int
    max_archive_bytes: int

    # Worker / taches
    task_soft_timeout: int
    task_hard_timeout: int
    task_max_age: int
    task_ttl: int
    active_job_ttl: int
    result_ttl: int
    worker_max_memory_kb: int

    # Retention
    poster_retention_days: int
    max_stored_posters: int

    # Divers
    environment: str
    enable_docs: bool
    log_level: str
    sentry_dsn: str | None
    sentry_traces_sample_rate: float
    nominatim_user_agent: str
    timezone: str
    geocode_timeout: int

    def __post_init__(self) -> None:
        if not _BUCKET_RE.fullmatch(self.s3_bucket):
            raise ConfigError(
                "S3_BUCKET doit respecter la syntaxe S3 (3-63 caracteres "
                "minuscules, chiffres, points ou tirets)."
            )
        if len(self.session_secret) < 32:
            raise ConfigError("SESSION_SECRET doit contenir au moins 32 caracteres.")
        if len(self.download_signing_secret) < 32:
            raise ConfigError(
                "DOWNLOAD_SIGNING_SECRET doit contenir au moins 32 caracteres."
            )
        if self.public_base_url and not self.public_base_url.startswith(
            ("http://", "https://")
        ):
            raise ConfigError(
                "PUBLIC_BASE_URL doit commencer par http:// ou https:// "
                "(ou rester vide)."
            )
        if self.cookie_secure not in {"auto", "true", "false"}:
            raise ConfigError("COOKIE_SECURE doit valoir auto, true ou false.")
        if not re.fullmatch(r"\d+/(second|minute|hour|day)", self.generate_rate_limit):
            raise ConfigError(
                "GENERATE_RATE_LIMIT doit respecter le format SlowAPI "
                "('<n>/<second|minute|hour|day>'), par exemple '5/minute'."
            )
        if self.task_hard_timeout <= self.task_soft_timeout:
            raise ConfigError(
                "TASK_TIME_LIMIT doit etre strictement superieur a "
                "TASK_SOFT_TIME_LIMIT."
            )

    @property
    def sentry_enabled(self) -> bool:
        return bool(self.sentry_dsn)


def load_settings() -> Settings:
    public_base_url = _raw("PUBLIC_BASE_URL") or ""
    public_base_url = public_base_url.rstrip("/")

    sentry_dsn = _raw("SENTRY_DSN")

    return Settings(
        redis_url=_required("REDIS_URL"),
        s3_endpoint_url=_optional("S3_ENDPOINT_URL", "http://storage:8333"),
        s3_bucket=_optional("S3_BUCKET", "posters"),
        s3_region=_optional("S3_REGION", "us-east-1"),
        s3_access_key=_required("S3_ACCESS_KEY"),
        s3_secret_key=_required("S3_SECRET_KEY"),
        session_secret=_required("SESSION_SECRET", min_length=32),
        download_signing_secret=_required("DOWNLOAD_SIGNING_SECRET", min_length=32),
        cookie_name="mp_session",
        cookie_secure=_optional("COOKIE_SECURE", "auto").lower(),
        session_ttl=_integer(
            "SESSION_TTL", 604800, minimum=300, maximum=30 * 86400
        ),
        download_ttl=_integer(
            "DOWNLOAD_URL_TTL", 900, minimum=60, maximum=7 * 86400
        ),
        public_base_url=public_base_url,
        generate_rate_limit=_optional("GENERATE_RATE_LIMIT", "5/minute"),
        daily_generate_quota=_integer(
            "DAILY_GENERATE_QUOTA", 50, minimum=1, maximum=10000
        ),
        max_active_jobs=_integer(
            "MAX_ACTIVE_JOBS_PER_SESSION", 2, minimum=1, maximum=10
        ),
        max_queued_jobs=_integer("MAX_QUEUED_JOBS", 20, minimum=1, maximum=1000),
        queue_name=_optional("CELERY_QUEUE", "celery"),
        max_distance_m=_integer(
            "MAX_DISTANCE_METERS", 25000, minimum=1000, maximum=100000
        ),
        max_output_pixels=_integer(
            "MAX_OUTPUT_PIXELS", 100_000_000, minimum=1_000_000, maximum=1_000_000_000
        ),
        max_dimension_inches=_integer(
            "MAX_IMAGE_DIMENSION_INCHES", 40, minimum=1, maximum=100
        ),
        max_dpi=_integer("MAX_RENDER_DPI", 600, minimum=72, maximum=1200),
        max_request_body_bytes=_integer(
            "MAX_REQUEST_BODY_BYTES", 131072, minimum=1024, maximum=10 * 1024 * 1024
        ),
        max_archive_bytes=_integer(
            "MAX_ARCHIVE_BYTES",
            512 * 1024 * 1024,
            minimum=1024 * 1024,
            maximum=4 * 1024 * 1024 * 1024,
        ),
        task_soft_timeout=_integer(
            "TASK_SOFT_TIME_LIMIT", 480, minimum=30, maximum=3600
        ),
        task_hard_timeout=_integer(
            "TASK_TIME_LIMIT", 540, minimum=60, maximum=7200
        ),
        task_max_age=_integer("TASK_MAX_AGE", 900, minimum=60, maximum=86400),
        task_ttl=_integer("TASK_RESULT_TTL", 3600, minimum=300, maximum=7 * 86400),
        active_job_ttl=_integer(
            "ACTIVE_JOB_TTL", 900, minimum=60, maximum=86400
        ),
        result_ttl=_integer("CELERY_RESULT_TTL", 3600, minimum=300, maximum=86400),
        worker_max_memory_kb=_integer(
            "WORKER_MAX_MEMORY_KB",
            1_500_000,
            minimum=100_000,
            maximum=8_000_000,
        ),
        poster_retention_days=_integer(
            "POSTER_RETENTION_DAYS", 7, minimum=0, maximum=3650
        ),
        max_stored_posters=_integer(
            "MAX_STORED_POSTERS", 2000, minimum=0, maximum=1_000_000
        ),
        environment=_optional("ENVIRONMENT", "production"),
        enable_docs=_boolean("ENABLE_DOCS", False),
        log_level=_optional("LOG_LEVEL", "INFO").upper(),
        sentry_dsn=sentry_dsn,
        sentry_traces_sample_rate=_float(
            "SENTRY_TRACES_SAMPLE_RATE", 0.1, minimum=0.0, maximum=1.0
        ),
        nominatim_user_agent=_optional(
            "NOMINATIM_USER_AGENT",
            "MapPoster/2.2 (+https://github.com/simongrossi/maptoposter-web)",
        ),
        timezone=_optional("TZ", "Europe/Paris"),
        geocode_timeout=_integer("GEOCODE_TIMEOUT", 10, minimum=1, maximum=60),
    )


settings = load_settings()
