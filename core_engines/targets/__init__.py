"""Targets: modelos e inteligencia de programas bug bounty."""

from core.targets.models import TargetIntel, Scope
from core.targets.hunter import Hunter
from core.targets.filters import (
    filter_targets_by_min_quality,
    filter_targets_by_max_complexity,
    filter_targets_by_platform,
)
from core.targets.parser import parse_program_scopes

__all__ = [
    "TargetIntel", "Scope", "Hunter",
    "filter_targets_by_min_quality", "filter_targets_by_max_complexity",
    "filter_targets_by_platform", "parse_program_scopes",
]
