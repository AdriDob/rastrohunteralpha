"""Response schema validation and contract compliance checking.

Used in debug/diagnostic mode to detect mismatches between
expected frontend schemas and actual backend responses.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("rastro.contracts.validator")

# ── Expected field sets for each contract ─────────────────────────────

EXPECTED_FIELDS: Dict[str, Set[str]] = {
    "target": {
        "id", "name", "domain", "payout", "score", "risk",
        "roi", "endpoints", "findings", "confirmedFindings",
        "competition", "freshness",
    },
    "opportunity": {
        "id", "targetId", "name", "domain", "payout", "score",
        "risk", "roi", "endpoints", "findings", "competition",
        "freshness", "surfaces", "vectors",
    },
    "endpoint": {
        "id", "targetId", "path", "method", "risk", "confidence",
        "vector", "labels", "signals", "attackSurface", "actionable",
    },
    "finding": {
        "id", "targetId", "endpointId", "title", "severity",
        "confidence", "status", "payout", "risk", "vector",
    },
    "evidence": {
        "id", "verdictId", "findingId", "requestUrl",
        "responseStatus", "consistent",
    },
}


def validate_contract(
    contract_name: str,
    data: Dict[str, Any],
    strict: bool = False,
) -> Tuple[bool, List[str]]:
    """Validate a dict against the expected contract.

    Returns (is_valid, list_of_issues).
    - strict=True: any unexpected field is an issue
    - strict=False: only missing required fields are issues
    """
    expected = EXPECTED_FIELDS.get(contract_name)
    if expected is None:
        return False, [f"Unknown contract: {contract_name}"]

    issues: List[str] = []
    actual_keys = set(data.keys())

    # Missing fields
    missing = expected - actual_keys
    for field in sorted(missing):
        issues.append(f"Missing field: {field}")

    if strict:
        unexpected = actual_keys - expected
        for field in sorted(unexpected):
            issues.append(f"Unexpected field: {field}")

    # Type checks for critical fields
    _check_type("id", data, int, issues)
    _check_type("payout", data, (int, float), issues)
    _check_type("score", data, (int, float), issues)
    _check_type("risk", data, (int, float), issues)
    _check_type("roi", data, (int, float), issues)

    is_valid = len(issues) == 0
    return is_valid, issues


def _check_type(field: str, data: Dict, expected_type, issues: List[str]) -> None:
    if field in data and data[field] is not None:
        if not isinstance(data[field], expected_type):
            issues.append(
                f"Type mismatch for '{field}': expected {expected_type.__name__}, "
                f"got {type(data[field]).__name__} ({data[field]!r})"
            )


def assert_contract_compliance(
    contract_name: str,
    data: Dict[str, Any],
    logger_instance=None,
) -> bool:
    """Check contract compliance, log warnings, return True if compliant."""
    log = logger_instance or logger
    is_valid, issues = validate_contract(contract_name, data)
    if not is_valid:
        for issue in issues:
            log.warning("[Contract] %s — %s", contract_name, issue)
    return is_valid


def validate_paginated_response(
    data: Dict[str, Any],
    contract_name: str,
) -> Dict[str, Any]:
    """Validate a paginated response.

    Returns a dict with:
      - total_items: int
      - valid_items: int
      - invalid_items: int
      - issues: List[str]
      - field_coverage: Dict[str, float]  (fraction of items with each field)
    """
    items = data.get("items", [])
    if not isinstance(items, list):
        return {
            "total_items": 0,
            "valid_items": 0,
            "invalid_items": 0,
            "issues": ["items is not a list"],
            "field_coverage": {},
        }

    expected = EXPECTED_FIELDS.get(contract_name, set())
    total = len(items)
    valid = 0
    field_hits: Dict[str, int] = {f: 0 for f in expected}
    all_issues: List[str] = []

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            all_issues.append(f"Item {i}: not a dict")
            continue
        is_valid, issues = validate_contract(contract_name, item)
        if is_valid:
            valid += 1
        else:
            all_issues.extend(f"Item {i}: {iss}" for iss in issues)
        for field in expected:
            if field in item and item[field] is not None:
                field_hits[field] = field_hits.get(field, 0) + 1

    coverage = {
        field: (hits / total * 100) if total > 0 else 0.0
        for field, hits in field_hits.items()
    }

    return {
        "total_items": total,
        "valid_items": valid,
        "invalid_items": total - valid,
        "issues": all_issues,
        "field_coverage": coverage,
    }


def build_debug_report() -> Dict[str, Any]:
    """Build a full debug report showing expected schemas and current state."""
    return {
        "contracts": {
            name: {
                "expected_fields": sorted(fields),
                "field_count": len(fields),
            }
            for name, fields in EXPECTED_FIELDS.items()
        },
        "version": "1.0",
    }
