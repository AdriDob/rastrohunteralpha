from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PlatformAction(str, Enum):
    PREPARE_ONLY = "prepare_only"
    PREPARE_AND_OPEN = "prepare_and_open"
    PREPARE_AND_FILL = "prepare_and_fill"
    AUTO_SUBMIT = "auto_submit"

    @classmethod
    def from_str(cls, s: str) -> PlatformAction:
        try:
            return cls(s)
        except ValueError:
            return cls.PREPARE_ONLY


@dataclass
class SubmissionResult:
    success: bool
    external_id: str = ""
    url: str = ""
    error: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class BugBountyPlatform(ABC):
    @property
    @abstractmethod
    def platform_id(self) -> str:
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        ...

    def supports_action(self, action: str | PlatformAction) -> bool:
        if isinstance(action, str):
            action = PlatformAction.from_str(action)
        if action == PlatformAction.PREPARE_ONLY:
            return True
        if action == PlatformAction.PREPARE_AND_OPEN:
            return True
        return self._supports_api_submission()

    def _supports_api_submission(self) -> bool:
        return False

    def prepare_report(self, report_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "platform": self.platform_id,
            "content": self._format_report(report_data),
            "submit_url": self._get_submit_url(report_data),
        }

    @abstractmethod
    def _format_report(self, report_data: dict[str, Any]) -> dict[str, Any]:
        ...

    @abstractmethod
    def _get_submit_url(self, report_data: dict[str, Any]) -> str:
        ...

    def submit(self, report_data: dict[str, Any], api_key: str) -> SubmissionResult:
        raise NotImplementedError(f"{self.platform_id} does not support API submission")

    def check_status(self, external_id: str) -> str:
        raise NotImplementedError(f"{self.platform_id} does not support status checking")
