"""Profile Exporter — exports investigator profile as JSON or Markdown."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .profile import ProfileService, get_profile_service


class ProfileExporter:
    """Export the investigator profile in various formats."""

    def __init__(self, profile_service: Optional[ProfileService] = None):
        self._profile = profile_service or get_profile_service()

    def to_json(self, user_id: str) -> str:
        stats = self._profile.get_stats(user_id)
        return json.dumps(stats, indent=2, default=str)

    def to_markdown(self, user_id: str) -> str:
        stats = self._profile.get_stats(user_id)
        if not stats.get("exists"):
            return "# Investigator Profile\n\n*No profile data yet.*"

        lines = ["# Investigator Profile"]
        lines.append(f"\n*Generated: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}Z*")
        lines.append(f"\n*Adaptive mode: {'Enabled' if stats.get('adaptive_mode') else 'Disabled'}*")

        # Discovery
        d = stats.get("discovery", {})
        lines.append("\n## Discovery")
        lines.append(f"- **Total Targets:** {d.get('total_targets', 0)}")
        if d.get("industries"):
            lines.append(f"- **Industries:** {', '.join(d['industries'])}")
        if d.get("technologies"):
            lines.append(f"- **Technologies:** {', '.join(d['technologies'])}")
        if d.get("programs"):
            lines.append(f"- **Programs:** {', '.join(d['programs'])}")
        if d.get("domains"):
            lines.append(f"- **Domains:** {', '.join(d['domains'])}")

        # Activity
        a = stats.get("activity", {})
        lines.append("\n## Activity")
        lines.append(f"- **Total Hours Active:** {a.get('total_hours_active', 0):.1f}")
        lines.append(f"- **Total Sessions:** {a.get('total_sessions', 0)}")
        lines.append(f"- **Average Session:** {a.get('average_session_minutes', 0):.1f} min")
        lines.append(f"- **Findings Per Session:** {a.get('average_findings_per_session', 0):.1f}")
        if a.get("favorite_modules"):
            modules = sorted(a["favorite_modules"], key=lambda x: x.get("count", 0), reverse=True)
            lines.append("- **Top Modules:**")
            for m in modules[:5]:
                lines.append(f"  - {m.get('module', m.get('name', '?'))}: {m.get('count', 0)} visits")

        # Preferences
        p = stats.get("preferences", {})
        lines.append("\n## Preferences")
        if p.get("favorite_bug_classes"):
            lines.append("- **Bug Classes:**")
            for c in sorted(p["favorite_bug_classes"], key=lambda x: x.get("count", 0), reverse=True):
                lines.append(f"  - {c.get('class', '?')}: {c.get('count', 0)} findings")
        if p.get("favorite_tools"):
            lines.append(f"- **Tools:** {', '.join(t.get('tool', '') for t in p['favorite_tools'])}")
        if p.get("favorite_asset_types"):
            lines.append(f"- **Asset Types:** {', '.join(t.get('name', '') for t in p['favorite_asset_types'])}")
        if p.get("preferred_ai_model"):
            lines.append(f"- **Preferred AI Model:** {p['preferred_ai_model']}")

        # Success History
        s = stats.get("success_history", {})
        lines.append("\n## Success History")
        lines.append(f"- **Confirmed Findings:** {s.get('confirmed_findings', 0)}")
        lines.append(f"- **Rejected Findings:** {s.get('rejected_findings', 0)}")
        lines.append(f"- **Duplicates Found:** {s.get('duplicates_found', 0)}")
        lines.append(f"- **Informational:** {s.get('informational_findings', 0)}")
        lines.append(f"- **High Severity:** {s.get('high_severity_findings', 0)}")
        lines.append(f"- **Avg Time to Validation:** {s.get('average_time_to_validation_hours', 0):.1f} hours")
        lines.append(f"- **Total ROI Estimate:** ${s.get('total_roi_estimate', 0):,.0f}")

        return "\n".join(lines)

    def export(self, user_id: str, fmt: str = "json") -> str:
        if fmt == "markdown":
            return self.to_markdown(user_id)
        return self.to_json(user_id)


_exporter: Optional[ProfileExporter] = None


def get_exporter() -> ProfileExporter:
    global _exporter
    if _exporter is None:
        _exporter = ProfileExporter()
    return _exporter
