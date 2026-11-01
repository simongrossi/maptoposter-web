"""Acces au stockage objet S3 prive (VersityGW ou tout S3 compatible).

Le bucket est cree au demarrage s'il n'existe pas. Il reste prive : aucune
policy anonyme n'est posee et le service de stockage n'est joignable que sur
le reseau Docker interne.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Iterator

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.response import StreamingBody

from backend.settings import settings

logger = logging.getLogger(__name__)

_client_lock = threading.Lock()
_client: Any = None
_bucket_ready = False

_NOT_FOUND_CODES = {"404", "NoSuchBucket", "NoSuchKey", "NotFound"}


def get_s3_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = boto3.client(
                    "s3",
                    endpoint_url=settings.s3_endpoint_url,
                    aws_access_key_id=settings.s3_access_key,
                    aws_secret_access_key=settings.s3_secret_key,
                    region_name=settings.s3_region,
                    config=Config(
                        signature_version="s3v4",
                        s3={"addressing_style": "path"},
                        connect_timeout=5,
                        read_timeout=120,
                        retries={"max_attempts": 3, "mode": "standard"},
                    ),
                )
    return _client


def _error_code(exc: ClientError) -> str:
    response = getattr(exc, "response", {}) or {}
    error = response.get("Error", {}) or {}
    return str(error.get("Code", "")) or str(
        response.get("ResponseMetadata", {}).get("HTTPStatusCode", "")
    )


def ensure_bucket() -> None:
    """Cree le bucket si necessaire. Idempotent et thread-safe."""
    global _bucket_ready
    if _bucket_ready:
        return

    s3 = get_s3_client()
    with _client_lock:
        if _bucket_ready:
            return
        try:
            s3.head_bucket(Bucket=settings.s3_bucket)
        except ClientError as exc:
            if _error_code(exc) not in _NOT_FOUND_CODES:
                raise
            try:
                s3.create_bucket(Bucket=settings.s3_bucket)
                logger.info("Bucket S3 cree: %s", settings.s3_bucket)
            except ClientError as create_exc:
                code = _error_code(create_exc)
                if code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                    raise
        _bucket_ready = True


def check_storage() -> None:
    """Leve une exception si le stockage ne repond pas."""
    get_s3_client().head_bucket(Bucket=settings.s3_bucket)


def object_exists(object_key: str) -> bool:
    try:
        get_s3_client().head_object(Bucket=settings.s3_bucket, Key=object_key)
        return True
    except ClientError as exc:
        if _error_code(exc) in _NOT_FOUND_CODES:
            return False
        raise


def upload_fileobj(fileobj, object_key: str, content_type: str) -> None:
    get_s3_client().upload_fileobj(
        fileobj,
        settings.s3_bucket,
        object_key,
        ExtraArgs={
            "ContentType": content_type,
            "CacheControl": "private, max-age=0",
            "ContentDisposition": f'inline; filename="{object_key}"',
        },
    )


def get_object(object_key: str) -> dict[str, Any]:
    return get_s3_client().get_object(
        Bucket=settings.s3_bucket, Key=object_key
    )


def head_object(object_key: str) -> dict[str, Any]:
    return get_s3_client().head_object(Bucket=settings.s3_bucket, Key=object_key)


def list_objects() -> list[dict[str, Any]]:
    s3 = get_s3_client()
    objects: list[dict[str, Any]] = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.s3_bucket):
        objects.extend(page.get("Contents", []) or [])
    return objects


def stream_object(object_key: str) -> tuple[StreamingBody, dict[str, Any]]:
    response = get_object(object_key)
    return response["Body"], response


def iter_body(body: StreamingBody, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
    try:
        for chunk in body.iter_chunks(chunk_size):
            if chunk:
                yield chunk
    finally:
        try:
            body.close()
        except Exception:
            pass


def _delete_keys(keys: Iterable[str]) -> None:
    key_list = [key for key in keys if key]
    if not key_list:
        return
    s3 = get_s3_client()
    for start in range(0, len(key_list), 1000):
        batch = key_list[start : start + 1000]
        try:
            s3.delete_objects(
                Bucket=settings.s3_bucket,
                Delete={"Objects": [{"Key": key} for key in batch], "Quiet": True},
            )
        except ClientError:
            # Certains backends S3 minimaux n'implementent pas DeleteObjects.
            for key in batch:
                try:
                    s3.delete_object(Bucket=settings.s3_bucket, Key=key)
                except ClientError as exc:
                    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
                    logger.warning(
                        "Suppression impossible (hash=%s): %s", key_hash, exc
                    )


def cleanup_old_objects(
    retention_days: int, max_objects: int
) -> tuple[int, int]:
    """Supprime les objets trop anciens ou au-dela du quota.

    Retourne (nombre examine, nombre supprime). Ne leve pas : le nettoyage est
    un mecanisme de defense en profondeur, pas une etape critique du rendu.
    """
    if retention_days <= 0 and max_objects <= 0:
        return (0, 0)

    try:
        objects = list_objects()
    except Exception as exc:  # pragma: no cover - depend du backend
        logger.warning("Nettoyage impossible, listing S3 en echec: %s", exc)
        return (0, 0)

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=retention_days) if retention_days > 0 else None

    # Du plus recent au plus ancien.
    def _last_modified(obj: dict[str, Any]) -> datetime:
        value = obj.get("LastModified")
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return now

    ordered = sorted(objects, key=_last_modified, reverse=True)
    to_delete: list[str] = []
    for index, obj in enumerate(ordered):
        key = obj.get("Key")
        if not key:
            continue
        if max_objects > 0 and index >= max_objects:
            to_delete.append(key)
            continue
        if cutoff is not None and _last_modified(obj) < cutoff:
            to_delete.append(key)

    if to_delete:
        _delete_keys(to_delete)
        logger.info(
            "Nettoyage stockage: %s objet(s) supprime(s) sur %s examines.",
            len(to_delete),
            len(objects),
        )
    return (len(objects), len(to_delete))
