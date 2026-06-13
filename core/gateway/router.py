"""Base router with unified response helpers.

All API routers should use these helpers to ensure consistent response format.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter as FastAPIRouter

from .schemas import APIEnvelope, PaginatedEnvelope, ok, error, paginated


class APIRouter(FastAPIRouter):
    """Base router that all API routers inherit from.

    Provides unified response helpers:
      - self.ok(data) -> normalized success response
      - self.error(msg) -> normalized error response
      - self.paginated(items, total, ...) -> normalized paginated response
    """

    def respond_ok(self, data: Any) -> APIEnvelope:
        return ok(data)

    def respond_error(self, msg: str) -> APIEnvelope:
        return error(msg)

    def respond_paginated(
        self,
        items: list,
        total: int,
        skip: int = 0,
        limit: int = 100,
    ) -> PaginatedEnvelope:
        return paginated(items, total, skip, limit)
