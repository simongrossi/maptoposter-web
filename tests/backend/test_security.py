import time

from backend.security import (
    build_download_url,
    decode_session,
    encode_session,
    sign_download,
    verify_download,
)


def test_session_roundtrip():
    session_id = "abcDEF123"
    cookie = encode_session(session_id)
    assert decode_session(cookie) == session_id


def test_session_tampering_is_rejected():
    cookie = encode_session("session-a")
    tampered = cookie.replace("session-a", "session-b")
    assert decode_session(tampered) is None


def test_expired_session_is_rejected():
    cookie = encode_session("session-a", issued_at=1)
    assert decode_session(cookie) is None


def test_signed_download_roundtrip():
    url = build_download_url("paris_noir_0123456789ab.png")
    assert url.startswith("/api/download/")
    assert "expires=" in url and "signature=" in url

    query = url.split("?", 1)[1]
    params = dict(part.split("=", 1) for part in query.split("&"))
    assert verify_download(
        "paris_noir_0123456789ab.png",
        int(params["expires"]),
        params["signature"],
    )


def test_signed_download_rejects_tampered_key():
    expires = int(time.time()) + 300
    signature = sign_download("paris.png", expires)
    assert not verify_download("berlin.png", expires, signature)


def test_signed_download_rejects_path_traversal():
    expires = int(time.time()) + 300
    signature = sign_download("../etc/passwd", expires)
    assert not verify_download("../etc/passwd", expires, signature)


def test_signed_download_rejects_expired():
    signature = sign_download("paris.png", 1)
    assert not verify_download("paris.png", 1, signature)
