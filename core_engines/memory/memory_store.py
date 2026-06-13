"""MemoryStore — durable persistence for decisions, insights, and execution traces."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database.db import SessionLocal
from database.models import MemoryRecord

logger = logging.getLogger("rastro.memory.store")

RETENTION_DAYS = 90


class MemoryStore:
    """Durable persistence layer for all memory categories.

    Supports decisions, insights, execution traces, and system outcomes.
    Every record has a category + key for efficient lookup.
    """

    def __init__(self) -> None:
        self.session = SessionLocal()

    def store(self, category: str, key: str, details: Dict[str, Any]) -> MemoryRecord:
        record = MemoryRecord(
            category=category,
            key=key,
            details=json.dumps(details),
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get(self, category: str, key: str) -> Optional[Dict[str, Any]]:
        record = (
            self.session.query(MemoryRecord)
            .filter(MemoryRecord.category == category)
            .filter(MemoryRecord.key == key)
            .order_by(MemoryRecord.created_at.desc())
            .first()
        )
        if record is None:
            return None
        return json.loads(record.details) if record.details else {}

    def query(
        self,
        category: str,
        key_prefix: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        q = self.session.query(MemoryRecord).filter(MemoryRecord.category == category)
        if key_prefix:
            q = q.filter(MemoryRecord.key.startswith(key_prefix))
        records = (
            q.order_by(MemoryRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        results = []
        for r in records:
            item = {"id": r.id, "key": r.key, "created_at": r.created_at.isoformat() if r.created_at else ""}
            if r.details:
                try:
                    item["details"] = json.loads(r.details)
                except json.JSONDecodeError:
                    item["details"] = r.details
            results.append(item)
        return results

    def delete(self, category: str, key: str) -> bool:
        deleted = (
            self.session.query(MemoryRecord)
            .filter(MemoryRecord.category == category)
            .filter(MemoryRecord.key == key)
            .delete()
        )
        self.session.commit()
        return deleted > 0

    def delete_older_than(self, category: str, days: int = RETENTION_DAYS) -> int:
        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted = (
            self.session.query(MemoryRecord)
            .filter(MemoryRecord.category == category)
            .filter(MemoryRecord.created_at < cutoff)
            .delete()
        )
        self.session.commit()
        return deleted

    def count(self, category: Optional[str] = None) -> int:
        q = self.session.query(MemoryRecord)
        if category:
            q = q.filter(MemoryRecord.category == category)
        return q.count()

    def categories(self) -> List[str]:
        records = (
            self.session.query(MemoryRecord.category)
            .distinct()
            .all()
        )
        return [r[0] for r in records]

    def close(self) -> None:
        self.session.close()


_STORE: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    global _STORE
    if _STORE is None:
        _STORE = MemoryStore()
    return _STORE
