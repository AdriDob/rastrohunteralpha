"""Information Reduction Engine — dedup, group, truncate, expand-on-demand.

Rules:
  - Remove semantic duplicates
  - Group similar metrics
  - Truncate verbose explanations by default
  - Expand-on-demand only

Usage:
    from core.ux.info_filter import reduce_briefing
    clean = reduce_briefing(raw_briefing)
"""

from __future__ import annotations

from typing import Any

MAX_DESCRIPTION_LENGTH = 120
MAX_REASON_LENGTH = 100
MAX_ACTIONS = 4
MAX_INSIGHTS = 1


def truncate(text: str | None, max_len: int = MAX_DESCRIPTION_LENGTH) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."


def dedup_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_labels: set = set()
    deduped = []
    for a in actions:
        key = a.get("label", "") or a.get("action", "")
        if key not in seen_labels:
            seen_labels.add(key)
            deduped.append(a)
    return deduped


def reduce_briefing(briefing: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}

    # Primary action
    recommended = briefing.get("recommended_action")
    if recommended:
        recommended["label"] = truncate(recommended.get("label"), 80)
        recommended["reason"] = truncate(recommended.get("reason"), MAX_REASON_LENGTH)
        output["recommended_action"] = recommended

    # Secondary actions (top 2)
    opportunities = briefing.get("opportunities", [])
    if opportunities:
        output["opportunities"] = dedup_actions(opportunities)[:2]

    # Critical risk
    risk = briefing.get("critical_risk")
    if risk:
        risk["description"] = truncate(risk.get("description"))
        output["critical_risk"] = risk

    # Quick win (merge info into secondary actions)
    quick_win = briefing.get("quick_win")
    if quick_win:
        quick_win["title"] = truncate(quick_win.get("title"))
        output["quick_win"] = quick_win

    # System insight (max 1 line)
    insight = briefing.get("assistant_insight")
    if insight:
        insight["focus"] = truncate(insight.get("focus"), 60)
        insight["reason"] = truncate(insight.get("reason"), MAX_REASON_LENGTH)
        output["assistant_insight"] = insight

    # System health (pass through, minimal)
    health = briefing.get("system_health")
    if health:
        output["system_health"] = health

    return output
