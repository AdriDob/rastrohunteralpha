"""FinancialAgent — tracks revenue, ROI, projections, and goals."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from core_engines.agents.base import BaseAgent
from core_engines.agents.types import AgentEvent, AgentId, EventType

logger = logging.getLogger("rastro.agents.financial")


class FinancialAgent(BaseAgent):
    """Tracks all revenue, ROI, projections, and financial goals.

    Aggregates data from:
    - Report payouts
    - Program statistics
    - Vulnerability type performance
    - Time tracking
    """

    def __init__(self, data_path: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.data_path = data_path or self._default_path()
        self._data: dict[str, Any] = self._load()

    @staticmethod
    def _default_path() -> str:
        home = os.environ.get("HOME", os.environ.get("USERPROFILE", "."))
        return os.path.join(home, ".rastro", "financial_data.json")

    def _get_agent_id(self) -> AgentId:
        return AgentId.FINANCIAL

    def _get_subscriptions(self) -> list[EventType | str]:
        return [
            EventType.FINANCIAL_UPDATED,
            EventType.FINANCIAL_PAYOUT_RECORDED,
            EventType.FINANCIAL_GOAL_UPDATED,
            EventType.DOCUMENTATION_COMPLETED,
        ]

    def handle_event(self, event: AgentEvent) -> None:
        handler_map = {
            EventType.FINANCIAL_UPDATED: self._on_update,
            EventType.FINANCIAL_PAYOUT_RECORDED: self._on_payout,
            EventType.FINANCIAL_GOAL_UPDATED: self._on_goal,
            EventType.DOCUMENTATION_COMPLETED: self._on_report_generated,
        }
        handler = handler_map.get(event.event_type)
        if handler:
            handler(event)

    def _on_update(self, event: AgentEvent) -> None:
        """Update financial metrics from payload."""
        for key, value in event.payload.items():
            if key in ("total_revenue", "monthly_revenue", "pending_rewards",
                       "paid_rewards", "accepted_reports", "submitted_reports"):
                self._data.setdefault("metrics", {})[key] = value

        self._data["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._save()

    def _on_payout(self, event: AgentEvent) -> None:
        """Record a confirmed payout."""
        payout = {
            "amount": event.payload.get("amount", 0),
            "currency": event.payload.get("currency", "USD"),
            "program": event.payload.get("program", ""),
            "vulnerability": event.payload.get("vulnerability", ""),
            "severity": event.payload.get("severity", ""),
            "date": event.payload.get("date", datetime.now(timezone.utc).isoformat()),
            "report_id": event.payload.get("report_id", ""),
        }
        self._data.setdefault("payouts", []).append(payout)
        self._recalculate_metrics()
        self._save()
        logger.info("[FINANCE] Payout recorded: %.2f %s from %s",
                    payout["amount"], payout["currency"], payout["program"])

    def _on_goal(self, event: AgentEvent) -> None:
        """Add or update a financial goal."""
        goal = {
            "id": event.payload.get("id", ""),
            "name": event.payload.get("name", ""),
            "target_amount": event.payload.get("target_amount", 0),
            "current_amount": event.payload.get("current_amount", 0),
            "currency": event.payload.get("currency", "USD"),
            "priority": event.payload.get("priority", "medium"),
            "deadline": event.payload.get("deadline", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        goals = self._data.setdefault("goals", [])
        existing = [g for g in goals if g.get("id") == goal["id"]]
        if existing:
            existing[0].update(goal)
        else:
            goals.append(goal)
        self._save()

    def _on_report_generated(self, event: AgentEvent) -> None:
        """Track report generation for bounty estimation."""
        reports = event.payload.get("reports", [])
        for r in reports:
            estimate = r.get("bounty_estimate", 0)
            if estimate:
                self._data.setdefault("report_estimates", []).append({
                    "title": r.get("title", ""),
                    "severity": r.get("severity", ""),
                    "estimate": estimate,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        self._recalculate_metrics()
        self._save()

    def _recalculate_metrics(self) -> None:
        payouts = self._data.get("payouts", [])
        estimates = self._data.get("report_estimates", [])

        total_paid = sum(p.get("amount", 0) for p in payouts)
        total_estimated = sum(e.get("estimate", 0) for e in estimates)

        # Per-program breakdown
        by_program: dict[str, float] = {}
        for p in payouts:
            prog = p.get("program", "unknown")
            by_program[prog] = by_program.get(prog, 0) + p.get("amount", 0)

        self._data["metrics"] = {
            "total_paid": total_paid,
            "total_estimated": total_estimated,
            "pending_revenue": max(0, total_estimated - total_paid),
            "payout_count": len(payouts),
            "estimate_count": len(estimates),
            "by_program": by_program,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    def get_summary(self) -> dict[str, Any]:
        """Return full financial summary."""
        metrics = self._data.get("metrics", {})
        goals = self._data.get("goals", [])

        # Goal progress
        enriched_goals = []
        for g in goals:
            target = g.get("target_amount", 1)
            current = g.get("current_amount", 0)
            progress = min(current / max(target, 1), 1.0)
            enriched_goals.append({
                **g,
                "progress_pct": round(progress * 100, 1),
                "remaining": max(0, target - current),
            })

        return {
            "metrics": metrics,
            "goals": enriched_goals,
            "payouts_count": len(self._data.get("payouts", [])),
            "estimates_count": len(self._data.get("report_estimates", [])),
        }

    def set_metric(self, key: str, value: Any) -> None:
        """Direct metric setter for dashboard initialization."""
        self._data.setdefault("metrics", {})[key] = value
        self._save()

    def add_goal(self, goal: dict[str, Any]) -> None:
        """Direct goal adder for dashboard initialization."""
        if "id" not in goal:
            from uuid import uuid4
            goal["id"] = uuid4().hex[:12]
        self._data.setdefault("goals", []).append(goal)
        self._save()

    def _load(self) -> dict[str, Any]:
        try:
            if os.path.exists(self.data_path):
                with open(self.data_path) as f:
                    return json.load(f)
        except Exception as exc:
            logger.warning("[FINANCE] Failed to load: %s", exc)
        return {"metrics": {}, "payouts": [], "goals": [], "report_estimates": []}

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
            with open(self.data_path, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception as exc:
            logger.warning("[FINANCE] Failed to save: %s", exc)


_FINANCIAL: FinancialAgent | None = None


def get_financial_agent() -> FinancialAgent:
    global _FINANCIAL
    if _FINANCIAL is None:
        _FINANCIAL = FinancialAgent()
    return _FINANCIAL
