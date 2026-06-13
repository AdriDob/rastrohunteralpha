"""Action Engine — converts every insight into a one-click executable action.

Rule: every insight must have an associated action. No passive elements.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("rastro.actions")

ActionHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass
class Action:
    id: str
    label: str
    action_type: str
    route: Optional[str] = None
    handler: Optional[ActionHandler] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "action_type": self.action_type,
            "route": self.route,
            "payload": self.payload,
            "requires_confirmation": self.requires_confirmation,
        }


class ActionEngine:
    """Registry of all executable actions. Each action has a handler or a route."""

    def __init__(self) -> None:
        self._actions: Dict[str, Action] = {}
        self._history: List[Dict[str, Any]] = []
        self._register_builtins()

    def _register_builtins(self) -> None:
        self.register(Action(
            id="open_target",
            label="Open Target",
            action_type="navigation",
            route="/target/{id}",
        ))
        self.register(Action(
            id="generate_report",
            label="Generate Report",
            action_type="action",
            route="/reports",
        ))
        self.register(Action(
            id="run_discovery",
            label="Run Discovery Engine",
            action_type="action",
            route="/pipeline",
        ))
        self.register(Action(
            id="refresh_intelligence",
            label="Refresh Intelligence",
            action_type="action",
            route="/intelligence",
        ))
        self.register(Action(
            id="mark_reviewed",
            label="Mark as Reviewed",
            action_type="feedback",
            handler=lambda p: {"status": "reviewed", "id": p.get("id")},
        ))
        self.register(Action(
            id="open_opportunity",
            label="View Opportunity",
            action_type="navigation",
            route="/radar",
        ))
        self.register(Action(
            id="view_evidence",
            label="Review Evidence",
            action_type="navigation",
            route="/evidence",
        ))
        self.register(Action(
            id="view_daily_briefing",
            label="Daily Briefing",
            action_type="navigation",
            route="/daily",
        ))

    def register(self, action: Action) -> None:
        self._actions[action.id] = action

    def get_action(self, action_id: str) -> Optional[Action]:
        return self._actions.get(action_id)

    def list_actions(self, action_type: Optional[str] = None) -> List[Action]:
        if action_type:
            return [a for a in self._actions.values() if a.action_type == action_type]
        return list(self._actions.values())

    def execute(self, action_id: str, payload: Optional[Dict[str, Any]] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        import time
        start = time.time()
        action = self._actions.get(action_id)
        if not action:
            return {"status": "error", "error": f"Unknown action: {action_id}"}

        result: Dict[str, Any] = {"action_id": action_id, "status": "executed"}
        error: Optional[str] = None

        if action.handler:
            try:
                result.update(action.handler(payload or {}))
            except Exception as exc:
                logger.warning("Action handler error: %s", exc)
                error = str(exc)
                result.update({"status": "error", "error": error})
        elif action.route:
            route = action.route
            if payload:
                route = route.format(**payload)
            result["route"] = route

        duration_ms = (time.time() - start) * 1000

        self._history.append({
            "action_id": action_id,
            "payload": payload,
            "user_id": user_id,
            "result": result,
            "duration_ms": round(duration_ms, 2),
        })
        if len(self._history) > 500:
            self._history = self._history[-500:]

        self._track_execution(action, payload, user_id, result, duration_ms, error)

        return result

    def _track_execution(
        self,
        action: Action,
        payload: Optional[Dict[str, Any]],
        user_id: Optional[str],
        result: Dict[str, Any],
        duration_ms: float,
        error: Optional[str],
    ) -> None:
        try:
            from core.actions.execution_tracker import get_execution_tracker
            tracker = get_execution_tracker()
            tracker.record_execution(
                action_id=action.id,
                action_type=action.action_type,
                label=action.label,
                status=result.get("status", "executed"),
                duration_ms=duration_ms,
                user_id=user_id,
                payload=payload,
                result=result,
                error=error,
            )
        except Exception as exc:
            logger.debug("Execution tracking error: %s", exc)

    def execute_by_priority(self, action_id: str, priority_payload: Dict[str, Any]) -> Dict[str, Any]:
        from core.intelligence.priority_engine import get_priority_engine
        engine = get_priority_engine()

        action = self._actions.get(action_id)
        if not action:
            return {"status": "error", "error": f"Unknown action: {action_id}"}

        result = self.execute(action_id, priority_payload.get("payload"))

        engine.ingest_user_signal(action_id, str(priority_payload.get("id", "")), weight=0.1)

        return result

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        type_counts: Dict[str, int] = {}
        for entry in self._history:
            action = self._actions.get(entry["action_id"])
            atype = action.action_type if action else "unknown"
            type_counts[atype] = type_counts.get(atype, 0) + 1
        stats = {
            "total_executed": len(self._history),
            "by_type": type_counts,
        }
        try:
            from core.actions.execution_tracker import get_execution_tracker
            tracker = get_execution_tracker()
            stats["execution_tracker"] = tracker.get_stats()
        except Exception:
            pass
        return stats


_ACTION_ENGINE: Optional[ActionEngine] = None


def get_action_engine() -> ActionEngine:
    global _ACTION_ENGINE
    if _ACTION_ENGINE is None:
        _ACTION_ENGINE = ActionEngine()
    return _ACTION_ENGINE
