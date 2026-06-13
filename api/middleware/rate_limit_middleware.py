from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core_engines.gateway.rate_limit import get_rate_limiter

# Paths excluded from rate limiting
NO_LIMIT_PREFIXES = {"/api/health", "/api/version", "/api/docs", "/api/openapi.json", "/api/redoc"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in NO_LIMIT_PREFIXES:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"{path}:{client_ip}"
        limiter = get_rate_limiter()

        if not limiter.consume(key):
            return JSONResponse(
                status_code=429,
                content={"error": "Too many requests", "retry_after": "1s"},
                headers={"X-RateLimit-Remaining": "0"},
            )

        remaining = limiter.remaining(key)
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(int(remaining))
        return response
