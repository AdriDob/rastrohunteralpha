"""Event Tracker — observes user behavior and updates the Investigator Profile.

Hooks into system events via the event bus to record behavioural metrics.
"""

from __future__ import annotations

from typing import Any

from .profile import ProfileService, get_profile_service


class EventTracker:
    """Observes user actions and updates the profile."""

    def __init__(self, profile_service: ProfileService | None = None):
        self._profile = profile_service or get_profile_service()

    # ── Public API ─────────────────────────────────────────────────────

    def track_target_viewed(self, user_id: str, target_data: dict[str, Any]) -> None:
        self._profile.increment(user_id, "total_targets")
        self._profile.append_json_list(user_id, "industries", target_data.get("industry"))
        self._profile.append_json_list(user_id, "technologies", target_data.get("technology"))
        self._profile.append_json_list(user_id, "programs", target_data.get("program"))
        self._profile.append_json_list(user_id, "domains", target_data.get("domain"))
        self._profile.log_event(user_id, "target_viewed", target_data)

    def track_finding_created(self, user_id: str, finding_data: dict[str, Any]) -> None:
        bug_class = finding_data.get("bug_class", "").lower()
        if bug_class:
            self._profile.increment_nested(user_id, "favorite_bug_classes", bug_class)
        severity = finding_data.get("severity", "").lower()
        if severity == "high" or severity == "critical":
            self._profile.increment(user_id, "high_severity_findings")
        is_duplicate = finding_data.get("duplicate", False)
        if is_duplicate:
            self._profile.increment(user_id, "duplicates_found")
        is_informational = severity == "informational" or severity == "info" or finding_data.get("is_informational", False)
        if is_informational:
            self._profile.increment(user_id, "informational_findings")
        self._profile.log_event(user_id, "finding_created", finding_data)

    def track_finding_validated(self, user_id: str, validation_data: dict[str, Any]) -> None:
        confirmed = validation_data.get("confirmed", False)
        if confirmed:
            self._profile.increment(user_id, "confirmed_findings")
            roi = validation_data.get("roi", 0)
            if roi:
                self._profile.increment(user_id, "total_roi_estimate", int(roi))
        else:
            self._profile.increment(user_id, "rejected_findings")
        validation_hours = validation_data.get("validation_hours", 0)
        if validation_hours:
            self._profile.update_field(user_id, "average_time_to_validation_hours", validation_hours)
        self._profile.log_event(user_id, "finding_validated", validation_data)

    def track_session_started(self, user_id: str) -> None:
        self._profile.increment(user_id, "total_sessions")
        self._profile.log_event(user_id, "session_started")

    def track_session_ended(self, user_id: str, duration_minutes: float = 0) -> None:
        self._profile.increment(user_id, "total_hours_active", int(duration_minutes / 60))
        self._profile.log_event(user_id, "session_ended", {"duration_minutes": duration_minutes})

    def track_module_visited(self, user_id: str, module: str) -> None:
        self._profile.increment_nested(user_id, "favorite_modules", module)
        self._profile.log_event(user_id, "module_visited", {"module": module})

    def track_tool_used(self, user_id: str, tool: str) -> None:
        self._profile.increment_nested(user_id, "favorite_tools", tool)
        self._profile.log_event(user_id, "tool_used", {"tool": tool})

    def track_asset_type(self, user_id: str, asset_type: str) -> None:
        self._profile.increment_nested(user_id, "favorite_asset_types", asset_type)
        self._profile.log_event(user_id, "asset_type_viewed", {"asset_type": asset_type})

    def track_preference_change(self, user_id: str, pref: str, value: Any) -> None:
        self._profile.update_field(user_id, pref, value)
        self._profile.log_event(user_id, "preference_changed", {pref: value})


_tracker: EventTracker | None = None


def get_event_tracker() -> EventTracker:
    global _tracker
    if _tracker is None:
        _tracker = EventTracker()
    return _tracker
