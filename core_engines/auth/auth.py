"""Lightweight token-based auth using HMAC-SHA256 JWT-like tokens.

No external dependencies — uses stdlib hmac, hashlib, json, time.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any

# Secret key — auto-generated on first import, persisted to env variable
_SECRET_KEY: str | None = None

TOKEN_TTL = 86400       # 24 hours
REFRESH_TTL = 2592000   # 30 days


def _get_secret() -> str:
    global _SECRET_KEY
    if _SECRET_KEY is None:
        _SECRET_KEY = os.environ.get(
            "RASTRO_AUTH_SECRET",
            hashlib.sha256(os.urandom(64)).hexdigest(),
        )
    return _SECRET_KEY


def _sign(payload: str) -> str:
    secret = _get_secret().encode("utf-8")
    return hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def create_token(data: dict[str, Any], ttl: int = TOKEN_TTL) -> str:
    """Create a signed token with the given data payload."""
    payload = {
        "data": data,
        "exp": int(time.time()) + ttl,
        "iat": int(time.time()),
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    sig = _sign(body)
    return f"{_b64(body)}.{sig}"


def verify_token(token: str) -> dict[str, Any] | None:
    """Verify and decode a token. Returns the data payload or None."""
    try:
        encoded_body, sig = token.split(".")
        body = _unb64(encoded_body)
        expected_sig = _sign(body)
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(body)
        if payload.get("exp", 0) < time.time():
            return None
        return payload.get("data")
    except (ValueError, json.JSONDecodeError):
        return None


def decode_token(token: str) -> dict[str, Any] | None:
    """Decode a token without verifying signature (for reading only)."""
    try:
        encoded_body = token.split(".")[0]
        return json.loads(_unb64(encoded_body))
    except (ValueError, json.JSONDecodeError, IndexError):
        return None


def create_session_token(user_id: str = "local", meta: dict[str, Any] | None = None) -> str:
    """Create a session token for a user/device."""
    data = {"sub": user_id, "meta": meta or {}}
    return create_token(data, ttl=TOKEN_TTL)


def create_refresh_token(user_id: str = "local") -> str:
    """Create a long-lived refresh token."""
    return create_token({"sub": user_id, "type": "refresh"}, ttl=REFRESH_TTL)


def verify_session(token: str) -> tuple[bool, dict[str, Any] | None]:
    """Verify a session token. Returns (is_valid, payload)."""
    data = verify_token(token)
    if data is None:
        return False, None
    return True, data


def _b64(s: str) -> str:
    """URL-safe base64 encode (no padding)."""
    import base64
    return base64.urlsafe_b64encode(s.encode("utf-8")).rstrip(b"=").decode("ascii")


def _unb64(s: str) -> str:
    """URL-safe base64 decode."""
    import base64
    # Add padding
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s).decode("utf-8")
