"""Adaptive Prioritizer — reorders recommendations based on investigator profile.

Every recommendation includes an explanation. No opaque decisions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .profile import ProfileService, get_profile_service


class PrioritizedItem:
    """A recommendation with attached explanation."""

    def __init__(self, item: Any, score: float, explanations: List[str]):
        self.item = item
        self.score = score
        self.explanations = explanations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item": self.item if isinstance(self.item, dict) else str(self.item),
            "score": round(self.score, 2),
            "explanations": self.explanations,
        }


class AdaptivePrioritizer:
    """Reorders items based on learned investigator profile."""

    def __init__(self, profile_service: Optional[ProfileService] = None):
        self._profile = profile_service or get_profile_service()

    def prioritize_targets(self, user_id: str, targets: List[Dict[str, Any]]) -> List[PrioritizedItem]:
        profile = self._profile.get(user_id)
        if not profile or not profile.adaptive_mode:
            return [PrioritizedItem(t, 0.0, []) for t in targets]

        result = []
        for t in targets:
            score = 0.0
            reasons = []

            # Preference match: industry
            if profile.industries and t.get("industry") in profile.industries:
                score += 15.0
                reasons.append(f"Industry '{t.get('industry')}' matches your previous investigations")

            # Preference match: technology
            if profile.technologies and t.get("technology") in profile.technologies:
                score += 12.0
                reasons.append(f"Technology '{t.get('technology')}' matches your expertise")

            # Preference match: program
            if profile.programs and t.get("program") in profile.programs:
                score += 10.0
                reasons.append(f"Program '{t.get('program')}' familiar from past work")

            # Preference match: domain pattern
            if profile.domains and t.get("domain") in profile.domains:
                score += 8.0
                reasons.append(f"Domain '{t.get('domain')}' previously investigated")

            # Success-based: high severity track record
            if profile.high_severity_findings > 5:
                score += 5.0
                reasons.append("You have a strong track record of finding high-severity issues")

            # Experience bonus
            if profile.confirmed_findings > 10:
                score += 3.0
                reasons.append("Experienced investigator — priority increased")

            result.append(PrioritizedItem(t, score, reasons))

        result.sort(key=lambda x: x.score, reverse=True)
        return result

    def prioritize_findings(self, user_id: str, findings: List[Dict[str, Any]]) -> List[PrioritizedItem]:
        profile = self._profile.get(user_id)
        if not profile or not profile.adaptive_mode:
            return [PrioritizedItem(f, 0.0, []) for f in findings]

        result = []
        favorite_classes = [c.get("class", "").lower() for c in (profile.favorite_bug_classes or []) if c.get("count", 0) > 0]

        for f in findings:
            score = 0.0
            reasons = []
            bug_class = f.get("bug_class", "").lower()

            if bug_class in favorite_classes:
                class_count = next(
                    (c.get("count", 0) for c in (profile.favorite_bug_classes or []) if c.get("class", "").lower() == bug_class),
                    0,
                )
                score += class_count * 1.5
                reasons.append(f"You have found {class_count} {bug_class} issues — this is in your area of expertise")

            severity = f.get("severity", "").lower()
            if severity in ("critical", "high"):
                score += 10.0
                reasons.append(f"{severity.capitalize()} severity — priority increased")

            if profile.confirmed_findings > 5:
                score += 2.0
                reasons.append("Your validation history improves confidence in this finding")

            result.append(PrioritizedItem(f, score, reasons))

        result.sort(key=lambda x: x.score, reverse=True)
        return result

    def prioritize_notifications(self, user_id: str, notifications: List[Dict[str, Any]]) -> List[PrioritizedItem]:
        """Filter and rank notifications by relevance."""
        profile = self._profile.get(user_id)
        if not profile or not profile.adaptive_mode:
            return [PrioritizedItem(n, 0.0, []) for n in notifications]

        result = []
        for n in notifications:
            score = 0.0
            reasons = []

            ntype = n.get("type", "")
            if ntype == "high_confidence":
                score += 30.0
                reasons.append("High confidence notification — matches your quality standards")
            elif ntype == "interesting_change":
                score += 15.0
                reasons.append("Target changed — similar to your past investigations")

            # Match against favorite technologies
            if profile.technologies and n.get("technology") in profile.technologies:
                score += 10.0
                reasons.append("Technology matches your expertise")

            # Match against favorite bug classes
            fav_classes = [c.get("class", "").lower() for c in (profile.favorite_bug_classes or [])]
            if n.get("bug_class", "").lower() in fav_classes:
                score += 8.0
                reasons.append("Bug class matches your strongest categories")

            result.append(PrioritizedItem(n, score, reasons))

        result.sort(key=lambda x: x.score, reverse=True)
        return result

    def daily_summary_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """Generate personalised daily summary recommendations."""
        profile = self._profile.get(user_id)
        recommendations = []
        if not profile:
            return recommendations

        top_classes = sorted(
            (profile.favorite_bug_classes or []),
            key=lambda x: x.get("count", 0),
            reverse=True,
        )[:3]
        if top_classes:
            class_names = ", ".join(c.get("class", "") for c in top_classes)
            recommendations.append({
                "type": "continue_strength",
                "message": f"Continue investigating {class_names} — your strongest categories",
                "explanation": f"Based on {sum(c.get('count', 0) for c in top_classes)} confirmed findings in these classes",
            })

        if profile.confirmed_findings > 0 and profile.rejected_findings > 0:
            ratio = profile.confirmed_findings / (profile.confirmed_findings + profile.rejected_findings)
            if ratio < 0.5:
                recommendations.append({
                    "type": "quality_tip",
                    "message": "Consider reviewing methodology — rejection rate is above 50%",
                    "explanation": f"{profile.rejected_findings} rejected out of {profile.confirmed_findings + profile.rejected_findings} total validations",
                })

        if profile.average_findings_per_session > 0:
            recommendations.append({
                "type": "productivity",
                "message": f"Average {profile.average_findings_per_session:.1f} findings per session",
                "explanation": "Tracked from your investigation history",
            })

        return recommendations


_prioritizer: Optional[AdaptivePrioritizer] = None


def get_prioritizer() -> AdaptivePrioritizer:
    global _prioritizer
    if _prioritizer is None:
        _prioritizer = AdaptivePrioritizer()
    return _prioritizer
