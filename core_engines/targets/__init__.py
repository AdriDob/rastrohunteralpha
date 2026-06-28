"""Targets: modelos e inteligencia de programas bug bounty."""

from core_engines.targets.filters import (
    filter_targets_by_max_complexity,
    filter_targets_by_min_quality,
    filter_targets_by_platform,
)
from core_engines.targets.hunter import Hunter
from core_engines.targets.models import Scope, TargetIntel
from core_engines.targets.parser import parse_program_scopes

__all__ = [
    "TargetIntel", "Scope", "Hunter",
    "filter_targets_by_min_quality", "filter_targets_by_max_complexity",
    "filter_targets_by_platform", "parse_program_scopes",
]
