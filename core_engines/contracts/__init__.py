"""
core.contracts — Canonical interfaces, base classes, and contract normalizers.
"""

from core_engines.contracts.base import (
    Artifact,
    ArtifactProtocol,
    Bundle,
    CacheProtocol,
    DependencyGraphProtocol,
    EventProtocol,
    InvalidationPolicy,
)
from core_engines.contracts.normalizers import (
    normalize_endpoint,
    normalize_evidence,
    normalize_finding,
    normalize_opportunity,
    normalize_overview,
    normalize_paginated,
    normalize_target,
)
from core_engines.contracts.validator import (
    EXPECTED_FIELDS,
    assert_contract_compliance,
    build_debug_report,
    validate_contract,
    validate_paginated_response,
)
from core_engines.contracts.wrapper import unwrap_items, unwrap_meta, wrap_list, wrap_paginated, wrap_single

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
