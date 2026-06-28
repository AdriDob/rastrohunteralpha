from __future__ import annotations

import logging
from typing import Any

from core_engines.platforms.base import BugBountyPlatform, SubmissionResult

logger = logging.getLogger("rastro.platforms.yeswehack")


class YesWeHack(BugBountyPlatform):
    @property
    def platform_id(self) -> str:
        return "yeswehack"

    @property
    def display_name(self) -> str:
        return "YesWeHack"

    def _supports_api_submission(self) -> bool:
        return True

    def _format_report(self, report_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": report_data.get("vulnerability", "Security Report"),
            "program": report_data.get("program", ""),
            "severity": report_data.get("severity", "medium"),
            "vulnerability_type": report_data.get("vulnerability", ""),
            "content": report_data.get("content", {}),
        }

    def _get_submit_url(self, report_data: dict[str, Any]) -> str:
        return "https://app.yeswehack.com/reports/new"

    def submit(self, report_data: dict[str, Any], api_key: str) -> SubmissionResult:
        formatted = self._format_report(report_data)
        try:
            import requests
            resp = requests.post(
                "https://api.yeswehack.com/v1/reports",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=formatted,
                timeout=30,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                ext_id = data.get("id", "")
                return SubmissionResult(
                    success=True,
                    external_id=str(ext_id),
                    url=f"https://app.yeswehack.com/reports/{ext_id}",
                    data=data,
                )
            return SubmissionResult(
                success=False,
                error=f"YesWeHack API error {resp.status_code}: {resp.text[:200]}",
            )
        except ImportError:
            return SubmissionResult(success=False, error="requests library not available")
        except Exception as exc:
            return SubmissionResult(success=False, error=str(exc))

    def check_status(self, external_id: str) -> str:
        try:
            import requests
            resp = requests.get(
                f"https://api.yeswehack.com/v1/reports/{external_id}",
                headers={"Authorization": "Bearer placeholder"},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("status", "unknown")
            return "unknown"
        except Exception:
            return "unknown"
