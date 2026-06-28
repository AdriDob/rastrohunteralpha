"""MemoryAgent — learns from previous reports, techniques, and outcomes."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from core_engines.agents.base import BaseAgent
from core_engines.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("rastro.agents.memory")


class MemoryAgent(BaseAgent):
    """Persistent memory across pipeline runs.

    Remembers:
    - Rejected techniques (don't try again on same program)
    - Successful chains (replicate on similar targets)
    - Accepted reports (what worked)
    - Duplicates (avoid wasting time)
    - Technology quirks per company
    - Company-specific behavior patterns
    """

    def __init__(self, memory_path: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.memory_path = memory_path or self._default_path()
        self._memory: dict[str, Any] = self._load()

    @staticmethod
    def _default_path() -> str:
        home = os.environ.get("HOME", os.environ.get("USERPROFILE", "."))
        return os.path.join(home, ".rastro", "agent_memory.json")

    def _get_agent_id(self) -> AgentId:
        return AgentId.MEMORY

    def _get_subscriptions(self) -> list[EventType | str]:
        return [
            EventType.MEMORY_STORE,
            EventType.MEMORY_RETRIEVED,
            EventType.VALIDATION_COMPLETED,
            EventType.EXPLOIT_COMPLETED,
            EventType.DOCUMENTATION_COMPLETED,
        ]

    def handle_event(self, event: AgentEvent) -> None:
        handler_map = {
            EventType.MEMORY_STORE: self._on_store,
            EventType.MEMORY_RETRIEVED: self._on_retrieve,
            EventType.VALIDATION_COMPLETED: self._on_validation,
            EventType.EXPLOIT_COMPLETED: self._on_exploit,
            EventType.DOCUMENTATION_COMPLETED: self._on_documentation,
        }
        handler = handler_map.get(event.event_type)
        if handler:
            handler(event)

    def _on_store(self, event: AgentEvent) -> None:
        key = event.payload.get("key", "")
        value = event.payload.get("value")
        namespace = event.payload.get("namespace", "general")

        if not key:
            return

        if namespace not in self._memory:
            self._memory[namespace] = {}
        self._memory[namespace][key] = {
            "value": value,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "source": event.source,
        }
        self._save()
        logger.info("[MEMORY] Stored %s/%s", namespace, key)

    def _on_retrieve(self, event: AgentEvent) -> None:
        key = event.payload.get("key", "")
        namespace = event.payload.get("namespace", "general")
        value = self._memory.get(namespace, {}).get(key)

        self.emit(
            EventType.MEMORY_RETRIEVED,
            payload={"key": key, "namespace": namespace, "value": value},
            target=event.source,
            correlation_id=event.correlation_id,
        )

    def _on_validation(self, event: AgentEvent) -> None:
        """Learn from validation results."""
        target = event.payload.get("target_name", "")
        confirmed = event.payload.get("confirmed_count", 0)
        total = len(event.payload.get("verdicts", {}))

        if target and total > 0:
            self._memory.setdefault("validation_history", []).append({
                "target": target,
                "confirmed": confirmed,
                "total": total,
                "ratio": round(confirmed / max(total, 1), 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            self._save()

    def _on_exploit(self, event: AgentEvent) -> None:
        """Learn from successful exploits."""
        confirmed = event.payload.get("confirmed", {})
        for _hp_key, data in confirmed.items():
            if data.get("confirmed"):
                technique = {
                    "path": data.get("path", ""),
                    "method": data.get("method", ""),
                    "confidence": data.get("confidence", 0),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                self._memory.setdefault("successful_techniques", []).append(technique)
        self._save()

    def _on_documentation(self, event: AgentEvent) -> None:
        """Track report generation history."""
        reports = event.payload.get("reports", [])
        for r in reports:
            self._memory.setdefault("reports_generated", []).append({
                "title": r.get("title", ""),
                "severity": r.get("severity", ""),
                "bounty_estimate": r.get("bounty_estimate", 0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        self._save()

    def remember(self, namespace: str, key: str) -> Any:
        """Direct retrieval (non-event)."""
        return self._memory.get(namespace, {}).get(key)

    def recall_all(self, namespace: str) -> dict[str, Any]:
        """Retrieve entire namespace."""
        return self._memory.get(namespace, {})

    def get_stats(self) -> dict[str, Any]:
        return {
            "namespaces": list(self._memory.keys()),
            "entries": sum(len(v) for v in self._memory.values() if isinstance(v, dict)),
            "validation_events": len(self._memory.get("validation_history", [])),
            "successful_techniques": len(self._memory.get("successful_techniques", [])),
            "reports_generated": len(self._memory.get("reports_generated", [])),
        }

    def _load(self) -> dict[str, Any]:
        try:
            if os.path.exists(self.memory_path):
                with open(self.memory_path) as f:
                    return json.load(f)
        except Exception as exc:
            logger.warning("[MEMORY] Failed to load: %s", exc)
        return {}

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
            with open(self.memory_path, "w") as f:
                json.dump(self._memory, f, indent=2)
        except Exception as exc:
            logger.warning("[MEMORY] Failed to save: %s", exc)


_MEMORY: MemoryAgent | None = None


def get_memory_agent() -> MemoryAgent:
    global _MEMORY
    if _MEMORY is None:
        _MEMORY = MemoryAgent()
    return _MEMORY
