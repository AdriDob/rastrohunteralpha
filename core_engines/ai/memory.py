"""
Short-term conversation memory for Rastro AI Assistant.

Keeps recent exchanges in memory. Persists important context
in the MemoryRecord database model for cross-session reference.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from database import db, models


class ConversationMemory:
    def __init__(self, max_exchanges: int = 20):
        self._exchanges: list[dict[str, str]] = []
        self._max = max_exchanges

    def add(self, role: str, content: str) -> None:
        self._exchanges.append({"role": role, "content": content, "timestamp": datetime.utcnow().isoformat()})
        if len(self._exchanges) > self._max:
            self._exchanges = self._exchanges[-self._max:]

    def recent(self, n: int = 5) -> list[dict[str, str]]:
        return [{"role": e["role"], "content": e["content"]} for e in self._exchanges[-n:]]

    def all(self) -> list[dict[str, str]]:
        return [{"role": e["role"], "content": e["content"]} for e in self._exchanges]

    def clear(self) -> None:
        self._exchanges.clear()

    def to_dict(self) -> dict[str, Any]:
        return {"exchange_count": len(self._exchanges), "recent": self.recent(5)}


_global_memory = ConversationMemory()


def get_memory() -> ConversationMemory:
    return _global_memory


def save_interaction(role: str, content: str, category: str = "assistant_chat") -> None:
    session = db.SessionLocal()
    try:
        record = models.MemoryRecord(
            category=category,
            key=f"{role}_{datetime.utcnow().timestamp()}",
            details=json.dumps({"role": role, "content": content[:1000]}),
        )
        session.add(record)
        session.commit()
    finally:
        session.close()


def get_recent_interactions(limit: int = 10) -> list[dict[str, Any]]:
    session = db.SessionLocal()
    try:
        records = (
            session.query(models.MemoryRecord)
            .filter(models.MemoryRecord.category == "assistant_chat")
            .order_by(models.MemoryRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        result = []
        for r in records:
            details = {}
            try:
                details = json.loads(r.details) if r.details else {}
            except (json.JSONDecodeError, TypeError):
                details = {"content": str(r.details)}
            result.append({
                "role": details.get("role", "unknown"),
                "content": details.get("content", ""),
                "timestamp": r.created_at.isoformat() if r.created_at else "",
            })
        return result
    finally:
        session.close()
