"""Standardized response wrapper — ensures every API list endpoint
returns the canonical shape:

{
  "items": [...],
  "meta": {
    "total": int,
    "skip": int,
    "limit": int
  }
}
"""

from __future__ import annotations

from typing import Any


def wrap_paginated(
    items: list[Any],
    total: int,
    skip: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    """Wrap items into the canonical paginated response shape."""
    return {
        "items": items,
        "meta": {
            "total": total,
            "skip": skip,
            "limit": limit,
        },
    }


def wrap_list(
    items: list[Any],
    total: int | None = None,
) -> dict[str, Any]:
    """Wrap a non-paginated list into canonical shape."""
    return {
        "items": items,
        "meta": {
            "total": total if total is not None else len(items),
            "skip": 0,
            "limit": len(items) if total is None else total,
        },
    }


def wrap_single(
    item: Any,
) -> dict[str, Any]:
    """Wrap a single item into canonical shape (list of one)."""
    return wrap_paginated([item], 1, 0, 1)


def unwrap_items(data: dict[str, Any]) -> list[Any]:
    """Safely extract items list from any response shape.

    Handles both old {items, total, skip, limit} and
    new {items, meta: {total, skip, limit}} formats.
    """
    if not isinstance(data, dict):
        return []
    items = data.get("items")
    if isinstance(items, list):
        return items
    return []


def unwrap_meta(data: dict[str, Any]) -> dict[str, int]:
    """Safely extract meta from any response shape."""
    if not isinstance(data, dict):
        return {"total": 0, "skip": 0, "limit": 0}

    meta = data.get("meta")
    if isinstance(meta, dict):
        return {
            "total": meta.get("total", 0),
            "skip": meta.get("skip", 0),
            "limit": meta.get("limit", 0),
        }

    # Fallback: flat total/skip/limit
    return {
        "total": data.get("total", 0),
        "skip": data.get("skip", 0),
        "limit": data.get("limit", 0),
    }
