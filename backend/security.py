"""Primitives de securite : sessions anonymes signees et URLs de telechargement.

Aucune dependance externe : HMAC-SHA256 via la bibliotheque standard.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import time
from typing import Optional
from urllib.parse import quote

from backend.settings import settings

# Identifiants d'objets acceptes : pas de separateur de chemin, pas de "..".
OBJECT_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,180}$")
# Identifiant de tache Celery (UUID) pour la route historique /download/{task_id}.
TASK_ID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")

_SESSION_MAX_LEN = 512


def _sign(message: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()


# ---------------------------------------------------------------------------
# Sessions anonymes
# ---------------------------------------------------------------------------


def new_session_id() -> str:
    """Identifiant opaque, non devinable, sans point (compatible cookie)."""
    return secrets.token_urlsafe(32)


def encode_session(session_id: str, issued_at: Optional[int] = None) -> str:
    iat = int(time.time()) if issued_at is None else int(issued_at)
    signature = _sign(f"session:{session_id}:{iat}", settings.session_secret)
    return f"{session_id}.{iat}.{signature}"


def decode_session(cookie_value: Optional[str]) -> Optional[str]:
    """Retourne l'identifiant de session si le cookie est valide et non expire."""
    if not cookie_value or len(cookie_value) > _SESSION_MAX_LEN:
        return None
    try:
        session_id, issued_raw, signature = cookie_value.rsplit(".", 2)
        issued_at = int(issued_raw)
    except (AttributeError, TypeError, ValueError):
        return None

    if not session_id or len(session_id) > 128:
        return None

    now = int(time.time())
    # Petite tolerance d'horloge, puis expiration stricte.
    if issued_at > now + 60:
        return None
    if now - issued_at > settings.session_ttl:
        return None

    expected = _sign(f"session:{session_id}:{issued_at}", settings.session_secret)
    if not hmac.compare_digest(signature, expected):
        return None
    return session_id


# ---------------------------------------------------------------------------
# URLs de telechargement signees
# ---------------------------------------------------------------------------


def _download_message(object_key: str, expires_at: int) -> str:
    return f"download:{object_key}:{expires_at}"


def sign_download(object_key: str, expires_at: int) -> str:
    return _sign(
        _download_message(object_key, int(expires_at)),
        settings.download_signing_secret,
    )


def verify_download(object_key: str, expires_at: int, signature: str) -> bool:
    if not OBJECT_KEY_RE.fullmatch(object_key):
        return False
    if not signature or len(signature) != 64:
        return False
    now = int(time.time())
    if expires_at <= now:
        return False
    # Une URL ne peut pas etre signee pour plus de 7 jours.
    if expires_at > now + 7 * 86400:
        return False
    expected = sign_download(object_key, expires_at)
    return hmac.compare_digest(signature, expected)


def build_download_url(object_key: str, ttl: Optional[int] = None) -> str:
    """Construit une URL signee, relative par defaut (meme origine)."""
    max_ttl = 7 * 86400
    effective_ttl = settings.download_ttl if ttl is None else int(ttl)
    effective_ttl = max(60, min(effective_ttl, max_ttl))
    expires_at = int(time.time()) + effective_ttl
    signature = sign_download(object_key, expires_at)
    path = (
        f"/api/download/{quote(object_key, safe='')}"
        f"?expires={expires_at}&signature={signature}"
    )
    base = settings.public_base_url.rstrip("/")
    return f"{base}{path}" if base else path
