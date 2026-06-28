"""Base agent — all specialized agents inherit from this."""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from core_engines.agents.bus import IEventBus, get_agent_bus
from core_engines.agents.types import AgentEvent, AgentId, AgentStatus, EventType

logger = logging.getLogger("rastro.agents.base")


class BaseAgent(ABC):
    """Abstract base for every agent in the system.

    Responsibilities:
    - Register with the event bus on start
    - Listen for relevant events
    - Process tasks via handle_event() — sync or async
    - Publish results back to the bus
    - Report health status
    """

    def __init__(self, bus: IEventBus | None = None) -> None:
        self.bus = bus or get_agent_bus()
        self.agent_id: AgentId = self._get_agent_id()
        self.name: str = self._get_name()
        self.capabilities: list[str] = self._get_capabilities()
        self.retry_policy: dict[str, Any] = self._get_retry_policy()
        self.status: AgentStatus = AgentStatus.OFFLINE
        self.tasks_completed: int = 0
        self.tasks_failed: int = 0
        self.total_time_ms: float = 0.0
        self.last_event: AgentEvent | None = None
        self.last_error: str | None = None
        self._running: bool = False
        self._subscription_types: list[str] = []

    @abstractmethod
    def _get_agent_id(self) -> AgentId:
        """Return this agent's unique identifier."""

    def _get_name(self) -> str:
        """Human-readable name (defaults to agent_id)."""
        return self.agent_id.value.replace("_", " ").title()

    def _get_capabilities(self) -> list[str]:
        """Return list of capability strings for this agent."""
        return [f"handles:{t.value if isinstance(t, EventType) else t}" for t in self._get_subscriptions()]

    def _get_retry_policy(self) -> dict[str, Any]:
        """Default retry policy (override per agent)."""
        return {"max_retries": 2, "backoff_s": 1.0, "backoff_multiplier": 2.0}

    @abstractmethod
    def _get_subscriptions(self) -> list[EventType | str]:
        """Return event types this agent handles."""

    @abstractmethod
    def handle_event(self, event: AgentEvent) -> None:
        """Process an incoming event. Can be sync or async."""

    def start(self) -> None:
        """Register with the bus and begin listening."""
        self.status = AgentStatus.IDLE
        self._running = True
        self._subscription_types.clear()
        self.bus.subscribe_agent(self.agent_id, self._on_event)
        self._subscription_types.append(self.agent_id.value)
        for event_type in self._get_subscriptions():
            key = event_type.value if isinstance(event_type, EventType) else event_type
            self.bus.subscribe(key, self._on_event)
            self._subscription_types.append(key)
        self.bus.publish(AgentEvent(
            event_type=EventType.AGENT_REGISTERED,
            source=self.agent_id,
            payload={
                "agent_id": self.agent_id.value,
                "name": self.name,
                "capabilities": self.capabilities,
                "status": self.status.value,
            },
        ))
        sub_count = len(self._get_subscriptions())
        logger.info("[AGENT] %s started, subscribed to %d event types, capabilities: %s",
                    self.agent_id.value, sub_count, self.capabilities)

    def stop(self) -> None:
        """Stop the agent and unsubscribe from the bus."""
        self._running = False
        self.status = AgentStatus.OFFLINE
        for event_type in getattr(self, '_subscription_types', []):
            self.bus.unsubscribe(event_type, self._on_event)
        self.bus.unsubscribe_agent(self.agent_id, self._on_event)
        self._subscription_types.clear()
        logger.info("[AGENT] %s stopped, subscriptions cleaned", self.agent_id.value)

    def subscribe(self, event_type: EventType | str, handler: Any = None) -> None:
        """Convenience: subscribe this agent to an additional event type."""
        target_handler = handler or self._on_event
        self.bus.subscribe(event_type, target_handler)

    def _on_event(self, event: AgentEvent) -> None:
        """Internal event dispatcher with timing and error handling."""
        if not self._running:
            return
        self.status = AgentStatus.WORKING
        self.last_event = event
        t0 = time.monotonic()
        try:
            result = self.handle_event(event)
            if inspect.iscoroutine(result):
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                if loop and loop.is_running():
                    asyncio.ensure_future(result)
                else:
                    asyncio.run(result)
            self.tasks_completed += 1
            elapsed = (time.monotonic() - t0) * 1000
            self.total_time_ms += elapsed
            self.status = AgentStatus.IDLE
        except Exception as exc:
            self.tasks_failed += 1
            self.last_error = str(exc)
            self.status = AgentStatus.ERROR
            elapsed = (time.monotonic() - t0) * 1000
            logger.error("[AGENT] %s error processing %s: %s (%.0fms)",
                         self.agent_id.value, event.event_type, exc, elapsed)
            self.bus.publish(AgentEvent(
                event_type=EventType.SYSTEM_ERROR,
                source=self.agent_id,
                target=AgentId.COORDINATOR,
                correlation_id=event.correlation_id,
                payload={
                    "error": str(exc),
                    "original_event": event.event_type,
                    "duration_ms": round(elapsed, 1),
                },
            ))

    def health(self) -> dict[str, Any]:
        """Return agent health snapshot."""
        avg_time = self.total_time_ms / max(self.tasks_completed, 1)
        return {
            "agent_id": self.agent_id.value,
            "name": self.name,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "avg_time_ms": round(avg_time, 1),
            "total_time_ms": round(self.total_time_ms, 1),
            "last_event": self.last_event.event_type if self.last_event else None,
            "last_error": self.last_error,
            "running": self._running,
        }

    def emit(self, event_type: EventType | str, payload: dict[str, Any],
             target: AgentId | None = None, correlation_id: str = "") -> None:
        """Helper to publish an event from this agent."""
        self.bus.publish(AgentEvent(
            event_type=event_type,
            source=self.agent_id,
            target=target,
            correlation_id=correlation_id,
            payload=payload,
        ))
