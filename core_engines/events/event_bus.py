"""Async-safe event bus — publish/subscribe for system-wide events.

Every event passes through the priority engine before being dispatched.
Events are classified: critical, high, medium, low, or ignore.
No event bypasses the prioritization layer.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections.abc import Callable
from enum import Enum
from typing import Any

logger = logging.getLogger("rastro.events")

EventHandler = Callable[..., Any]


class EventPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    IGNORE = "ignore"


EVENT_PRIORITY_MAP: dict[str, str] = {
    "system:error": "critical",
    "system:degraded": "critical",
    "system:alert": "critical",
    "recovery:started": "critical",
    "recovery:failed": "critical",
    "anomaly_detected": "critical",
    "failure_predicted": "critical",
    "opportunity:found": "high",
    "quick_win:detected": "high",
    "contract:warning": "high",
    "system:ready": "medium",
    "recovery:success": "medium",
    "health_score_updated": "medium",
    "auto_optimization_applied": "medium",
    "report:generated": "medium",
    "opportunity:updated": "medium",
    "assistant:recommendation": "medium",
    "sync:completed": "low",
    "discovery:completed": "low",
    "system:boot:complete": "low",
    "system:boot:starting": "low",
}


def classify_event(event_type: str) -> str:
    return EVENT_PRIORITY_MAP.get(event_type, "medium")


class EventBus:
    """Lightweight in-process event bus.

    Every publish() call:
      1. Classifies the event via priority map
      2. Routes through priority engine for ranking
      3. Dispatches to sync + async handlers
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._handlers: dict[str, list[EventHandler]] = {}
        self._async_handlers: dict[str, list[EventHandler]] = {}
        self._history: list[dict[str, Any]] = []
        self._max_history = 500

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register a sync handler for an event type.
        Use "*" to subscribe to all events.
        """
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)

    def subscribe_async(self, event_type: str, handler: EventHandler) -> None:
        """Register an async handler for an event type.
        Use "*" to subscribe to all events.
        """
        with self._lock:
            if event_type not in self._async_handlers:
                self._async_handlers[event_type] = []
            self._async_handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a handler from an event type."""
        with self._lock:
            if event_type in self._handlers:
                self._handlers[event_type] = [h for h in self._handlers[event_type] if h != handler]
            if event_type in self._async_handlers:
                self._async_handlers[event_type] = [h for h in self._async_handlers[event_type] if h != handler]

    def publish(self, event_type: str, **payload: Any) -> None:
        """Publish an event. Classifies → routes through priority → dispatches."""
        priority = classify_event(event_type)

        payload["_priority"] = priority
        with self._lock:
            _record_event(self._history, self._max_history, event_type, priority, payload)

        if priority == "ignore":
            logger.debug("Ignored event: %s", event_type)
            return

        # Route through priority engine for ranking
        try:
            from core_engines.intelligence.priority_engine import get_priority_engine
            engine = get_priority_engine()
            if event_type.startswith("opportunity"):
                engine.ingest_opportunity({"source": "opportunity", **payload})
            elif event_type.startswith("quick_win"):
                engine.ingest_quick_win({"source": "quick_win", **payload})
            elif event_type in ("system:error", "system:degraded", "system:ready"):
                engine.ingest_system_alert({
                    "source": "alert",
                    "severity": priority,
                    "title": event_type,
                    "message": payload.get("message", str(payload)),
                    **payload,
                })
        except Exception as exc:
            logger.debug("Priority routing skipped: %s", exc)

        # Sync handlers (exact match + wildcard)
        with self._lock:
            handlers = list(self._handlers.get(event_type, [])) + list(self._handlers.get("*", []))
        for handler in handlers:
            try:
                handler(event_type=event_type, priority=priority, **payload)
            except Exception as exc:
                logger.warning("Event handler error on %s: %s", event_type, exc)

        # Async handlers — fire and forget (exact match + wildcard)
        with self._lock:
            async_handlers = list(self._async_handlers.get(event_type, [])) + list(self._async_handlers.get("*", []))
        if async_handlers:
            loop = _get_loop()
            if loop is None or loop.is_closed():
                logger.debug("No running event loop for async handlers of %s", event_type)
            else:
                for handler in async_handlers:
                    try:
                        fut = asyncio.run_coroutine_threadsafe(
                            handler(event_type=event_type, priority=priority, **payload), loop,
                        )
                        fut.add_done_callback(
                            lambda f: logger.warning("Async handler error on %s: %s", event_type, f.exception())
                            if f.exception() else None
                        )
                    except Exception as exc:
                        logger.warning("Async event handler error on %s: %s", event_type, exc)

    def get_history(self, event_type: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent events, optionally filtered by type."""
        with self._lock:
            if event_type:
                return [e for e in self._history if e["type"] == event_type][-limit:]
            return self._history[-limit:]

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    def handler_count(self, event_type: str | None = None) -> int:
        with self._lock:
            if event_type:
                return len(self._handlers.get(event_type, [])) + len(self._async_handlers.get(event_type, []))
            return sum(len(v) for v in self._handlers.values()) + sum(len(v) for v in self._async_handlers.values())


def _record_event(history: list[dict[str, Any]], max_history: int, event_type: str, priority: str, payload: dict[str, Any]) -> None:
    history.append({
        "type": event_type,
        "priority": priority,
        "timestamp": time.time(),
        "payload": payload,
    })
    if len(history) > max_history:
        history[:] = history[-max_history:]


def _get_loop() -> asyncio.AbstractEventLoop | None:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


_BUS: EventBus | None = None


def get_event_bus() -> EventBus:
    global _BUS
    if _BUS is None:
        _BUS = EventBus()
        logger.info("Event bus initialized")
    return _BUS
