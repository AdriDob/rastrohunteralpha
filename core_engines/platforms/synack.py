from __future__ import annotations

import logging
from typing import Any

from core_engines.platforms.base import BugBountyPlatform

logger = logging.getLogger("rastro.platforms.synack")


class Synack(BugBountyPlatform):
    @property
    def platform_id(self) -> str:
        return "synack"

    @property
    def display_name(self) -> str:
        return "Synack"

    def _supports_api_submission(self) -> bool:
        return False

    def _format_report(self, report_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": report_data.get("vulnerability", "Security Finding"),
            "program": report_data.get("program", ""),
            "severity": report_data.get("severity", "medium"),
            "content": report_data.get("content", {}),
        }

    def _get_submit_url(self, report_data: dict[str, Any]) -> str:
        return "https://synack.com/red-team/reporting"
