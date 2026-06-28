"""
intelligence.event_system — Internal event system for incremental updates.

Allows components to emit and subscribe to events.
Enables incremental recomputation without full pipeline reruns.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

LOG = logging.getLogger("rastro.intelligence.event_system")

# Canonical event types
EVENT_TYPES = {
    "NewEndpoint",
    "PipelineUpdated",
    "EvidenceAdded",
    "VerdictChanged",
    "ReportGenerated",
    "ScreenshotUpdated",
    "DifferentialUpdated",
    "AIInsightUpdated",
    "QuickWinsUpdated",
    "ExecutionPlanUpdated",
    "AttackSurfaceUpdated",
    "ROIUpdated",
    "HypothesisUpdated",
    "CacheHit",
    "CacheMiss",
    "ArtifactInvalidated",
}

EventHandler = Callable[[str, Any], None]


@dataclass
class Event:
    event_type: str
    payload: Any
    timestamp: str = ""
    event_id: int = 0

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


class EventSystem:
    """
    Simple pub/sub event system.

    Events enable incremental updates:
    - When PipelineUpdated fires, subscribers can recompute only affected artifacts
    - When EvidenceAdded fires, AI Assistant can regenerate insights without full rerun
    """

    def __init__(self, max_history: int = 500) -> None:
        self._lock = threading.Lock()
        self._subscribers: dict[str, list[EventHandler]] = {}
        self._history: dict[str, list[Event]] = {}
        self._all_events: list[Event] = []
        self._event_counter: int = 0
        self._max_history = max_history

    def emit(self, event_type: str, payload: Any = None) -> None:
        if event_type not in EVENT_TYPES:
            LOG.warning("Unknown event type: %s", event_type)
        with self._lock:
            self._event_counter += 1
            event = Event(
                event_type=event_type,
                payload=payload,
                event_id=self._event_counter,
            )
            self._all_events.append(event)
            if len(self._all_events) > self._max_history:
                self._all_events = self._all_events[-self._max_history:]
            if event_type not in self._history:
                self._history[event_type] = []
            self._history[event_type].append(event)
            if len(self._history[event_type]) > self._max_history:
                self._history[event_type] = self._history[event_type][-self._max_history:]
            event_id = event.event_id
        LOG.debug("Event: %s (#%d)", event_type, event_id)
        for handler in self._subscribers.get(event_type, []):
            try:
                handler(event_type, payload)
            except Exception as exc:
                LOG.error("Event handler error for %s: %s", event_type, exc)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in EVENT_TYPES:
            LOG.warning("Subscribing to unknown event type: %s", event_type)
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)
                LOG.debug("Subscribed to %s", event_type)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type] = [
                    h for h in self._subscribers[event_type] if h != handler
                ]

    def get_events(self, event_type: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            events = self._history.get(event_type, []) if event_type else self._all_events
            return [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "timestamp": e.timestamp,
                    "payload": e.payload,
                }
                for e in events
            ]

    def clear(self) -> None:
        with self._lock:
            self._history.clear()
            self._all_events.clear()
            self._event_counter = 0

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "total_events": len(self._all_events),
                "event_types": {
                    et: len(evts) for et, evts in self._history.items()
                },
                "subscribers": {
                    et: len(handlers) for et, handlers in self._subscribers.items()
                },
            }


_global_event_system: EventSystem | None = None
_global_event_system_lock = threading.Lock()


def get_event_system() -> EventSystem:
    global _global_event_system
    if _global_event_system is None:
        with _global_event_system_lock:
            if _global_event_system is None:
                _global_event_system = EventSystem()
    return _global_event_system
