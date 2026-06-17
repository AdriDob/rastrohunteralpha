"""Memory Builder — builds contextual memory for the AI assistant.

Provides relevant context about the investigator's profile and history
without exposing sensitive information externally.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .profile import ProfileService, get_profile_service


class MemoryBuilder:
    """Builds contextual prompts for the AI assistant."""

    def __init__(self, profile_service: Optional[ProfileService] = None):
        self._profile = profile_service or get_profile_service()

    def build_context(self, user_id: str, target_context: Optional[Dict[str, Any]] = None) -> str:
        """Build a context string for AI assistant prompts."""
        profile = self._profile.get(user_id)
        if not profile:
            return ""

        parts = ["[INVESTIGATOR PROFILE]"]

        if profile.industries:
            parts.append(f"Investigated industries: {', '.join(profile.industries)}")
        if profile.technologies:
            parts.append(f"Known technologies: {', '.join(profile.technologies)}")

        top_classes = sorted(
            (profile.favorite_bug_classes or []),
            key=lambda x: x.get("count", 0),
            reverse=True,
        )[:3]
        if top_classes:
            parts.append(f"Strongest bug classes: {', '.join(c['class'] for c in top_classes)}")

        if profile.confirmed_findings > 0:
            parts.append(f"Confirmed findings: {profile.confirmed_findings}")

        # Similarity match against target context
        if target_context:
            matches = []
            if target_context.get("industry") in (profile.industries or []):
                matches.append(f"Industry '{target_context.get('industry')}' resembles previous investigations")
            if target_context.get("technology") in (profile.technologies or []):
                matches.append(f"Technology '{target_context.get('technology')}' matches past work")

            if matches:
                parts.append("Target context matches:")
                parts.extend(f"  - {m}" for m in matches)

        parts.append("[END PROFILE]")
        return "\n".join(parts)

    def find_similar_findings(self, user_id: str, bug_class: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Find past successful findings similar to a given bug class."""
        profile = self._profile.get(user_id)
        if not profile:
            return []

        for c in (profile.favorite_bug_classes or []):
            if c.get("class", "").lower() == bug_class.lower() and c.get("count", 0) > 0:
                return [{
                    "type": "similar_finding",
                    "bug_class": bug_class,
                    "count": c["count"],
                    "note": f"This looks similar to finding patterns you have validated {c['count']} times before.",
                }]
        return []

    def investigation_tip(self, user_id: str, target: Dict[str, Any]) -> Optional[str]:
        """Generate a personalised tip based on the target and profile."""
        profile = self._profile.get(user_id)
        if not profile or not profile.adaptive_mode:
            return None

        reasons = []
        if target.get("technology") in (profile.technologies or []):
            reasons.append(f"focus on {target['technology']} endpoints")
        for c in (profile.favorite_bug_classes or []):
            if c.get("count", 0) > 3:
                reasons.append(f"check for {c['class']} vulnerabilities")
                break
        if profile.confirmed_findings > 10:
            reasons.append("apply your usual validation methodology")

        if not reasons:
            return None

        return "Tip: " + ", ".join(reasons) + "."


_memory_builder: Optional[MemoryBuilder] = None


def get_memory_builder() -> MemoryBuilder:
    global _memory_builder
    if _memory_builder is None:
        _memory_builder = MemoryBuilder()
    return _memory_builder
