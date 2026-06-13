"""
core.contracts — Canonical interfaces, base classes, and contract normalizers.
"""

from core.contracts.base import Artifact, Bundle, ArtifactProtocol, DependencyGraphProtocol, EventProtocol, CacheProtocol, InvalidationPolicy
from core.contracts.normalizers import normalize_target, normalize_opportunity, normalize_endpoint, normalize_finding, normalize_evidence, normalize_overview, normalize_paginated
from core.contracts.validator import validate_contract, assert_contract_compliance, validate_paginated_response, build_debug_report, EXPECTED_FIELDS
from core.contracts.wrapper import wrap_paginated, wrap_list, wrap_single, unwrap_items, unwrap_meta

__all__ = [
    "Artifact", "Bundle", "ArtifactProtocol", "DependencyGraphProtocol",
    "EventProtocol", "CacheProtocol", "InvalidationPolicy",
    "normalize_target", "normalize_opportunity", "normalize_endpoint",
    "normalize_finding", "normalize_evidence", "normalize_overview",
    "normalize_paginated",
    "validate_contract", "assert_contract_compliance",
    "validate_paginated_response", "build_debug_report", "EXPECTED_FIELDS",
    "wrap_paginated", "wrap_list", "wrap_single", "unwrap_items", "unwrap_meta",
]
