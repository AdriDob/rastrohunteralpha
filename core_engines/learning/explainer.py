"""Explainer — generates human-readable explanations for recommendations.

Every recommendation must include a reason. No opaque decisions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .profile import ProfileService, get_profile_service


class Explainer:
    """Generates explanations for profile-driven recommendations."""

    def __init__(self, profile_service: Optional[ProfileService] = None):
        self._profile = profile_service or get_profile_service()

    def why_priority_increased(self, user_id: str, item_type: str, item: Dict[str, Any]) -> List[str]:
        """Explain why an item was prioritised higher."""
        profile = self._profile.get(user_id)
        if not profile:
            return ["Adaptive mode disabled — no profile data"]

        reasons = []

        if item_type == "target":
            if item.get("industry") in (profile.industries or []):
                reasons.append(f"Industry '{item.get('industry')}' matches your previous investigations")
            if item.get("technology") in (profile.technologies or []):
                reasons.append(f"Technology '{item.get('technology')}' matches your expertise")
            if profile.confirmed_findings > 10:
                reasons.append("Experienced investigator — priority increased")

        elif item_type == "finding":
            bug_class = item.get("bug_class", "").lower()
            for c in (profile.favorite_bug_classes or []):
                if c.get("class", "").lower() == bug_class and c.get("count", 0) > 0:
                    reasons.append(f"You have found {c['count']} {bug_class} issues — expertise match")
                    break
            severity = item.get("severity", "").lower()
            if severity in ("critical", "high"):
                reasons.append(f"{severity.capitalize()} severity finding")
            if profile.confirmed_findings > 5:
                reasons.append("Your validation history supports this finding")

        elif item_type == "notification":
            ntype = item.get("type", "")
            if ntype == "high_confidence":
                reasons.append("High confidence notification")
            if item.get("technology") in (profile.technologies or []):
                reasons.append("Technology matches your expertise")
            bug_class = item.get("bug_class", "").lower()
            for c in (profile.favorite_bug_classes or []):
                if c.get("class", "").lower() == bug_class and c.get("count", 0) > 0:
                    reasons.append(f"Bug class '{c['class']}' is your specialty")
                    break

        if not reasons:
            reasons.append("No strong profile match — default priority")

        return reasons

    def profile_summary(self, user_id: str) -> str:
        """Generate a plain-text summary of the investigator profile."""
        profile = self._profile.get(user_id)
        if not profile:
            return "No profile data yet."

        lines = ["=== INVESTIGATOR PROFILE ==="]
        lines.append(f"Targets: {profile.total_targets}")
        lines.append(f"Confirmed findings: {profile.confirmed_findings}")
        lines.append(f"High severity: {profile.high_severity_findings}")
        lines.append(f"Total hours: {profile.total_hours_active:.1f}")
        lines.append(f"Sessions: {profile.total_sessions}")

        bug_classes = sorted(
            (profile.favorite_bug_classes or []),
            key=lambda x: x.get("count", 0),
            reverse=True,
        )[:5]
        if bug_classes:
            lines.append(f"Top bug classes: {', '.join(c['class'] for c in bug_classes)}")

        industries = (profile.industries or [])
        if industries:
            lines.append(f"Industries: {', '.join(industries)}")

        technologies = (profile.technologies or [])
        if technologies:
            lines.append(f"Technologies: {', '.join(technologies)}")

        return "\n".join(lines)


_explainer: Optional[Explainer] = None


def get_explainer() -> Explainer:
    global _explainer
    if _explainer is None:
        _explainer = Explainer()
    return _explainer
