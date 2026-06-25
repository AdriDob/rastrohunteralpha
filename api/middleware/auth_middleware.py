import logging
import os
import re
from typing import Set

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core_engines.auth.session_validator import get_session_validator
from core_engines.license import is_license_valid
from core_engines.license.hardware import get_hardware_id

logger = logging.getLogger("rastro.auth.middleware")

_DIAG_LOG = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "Rastro", "license_diagnostic.log",
)
def _diag(msg: str) -> None:
    try:
        os.makedirs(os.path.dirname(_DIAG_LOG), exist_ok=True)
        with open(_DIAG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[AUTH-MIDDLEWARE] {msg}\n")
    except Exception:
        pass

# Paths that do NOT require authentication
PUBLIC_PATHS: Set[str] = {
    "/api/health",
    "/api/version",
    "/api/docs",
    "/api/openapi.json",
    "/api/redoc",
}

# Prefixes that do NOT require authentication
PUBLIC_PREFIXES: Set[str] = {
    "/api/auth",
    "/api/license",
}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # WebSocket connections are handled by their own auth (token in query param)
        if request.scope["type"] == "websocket":
            return await call_next(request)

        path = request.url.path

        # Desktop mode: non-API paths are frontend assets, never require auth
        if not path.startswith("/api/"):
            return await call_next(request)

        if path in PUBLIC_PATHS:
            return await call_next(request)

        if any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()

        if not token:
            return JSONResponse(
                status_code=401,
                content={"error": "Authorization header required"},
            )

        validator = get_session_validator()
        result = validator.validate(token)

        if not result.valid:
            return JSONResponse(
                status_code=401,
                content={"error": result.reason or "Invalid or expired token"},
            )

        # License check — skip for public/auth/license paths
        _diag(f"License check triggered for path={path}")
        current_hwid = get_hardware_id()
        _diag(f"CURRENT HWID = {current_hwid}")
        valid_license, reason = is_license_valid()
        _diag(f"LICENSE VALID = {valid_license}")
        _diag(f"LICENSE ERROR = {reason}")
        if not valid_license:
            _diag(f"LICENSE REJECTED: {reason}")
        if not valid_license and path not in PUBLIC_PATHS and not any(
            path.startswith(p) for p in PUBLIC_PREFIXES
        ):
            _diag(f"Returning 403 for {path}: {reason}")
            return JSONResponse(
                status_code=403,
                content={"error": "License required", "detail": "Activate at /api/license/activate"},
            )

        return await call_next(request)
