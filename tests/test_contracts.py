"""Lightweight contract compliance tests.

Validates that:
  - No missing required fields after normalization
  - No naming mismatches (snake_case vs camelCase)
  - Response shape consistency
"""

from __future__ import annotations

from typing import Any, Dict, List

# ── Expected DTO fields (camelCase) ───────────────────────────────────

EXPECTED_TARGET_FIELDS = {
    "id", "name", "domain", "payout", "score", "risk",
    "roi", "endpoints", "findings", "confirmedFindings",
    "competition", "freshness",
}

EXPECTED_OPPORTUNITY_FIELDS = {
    "id", "targetId", "name", "domain", "payout", "score",
    "risk", "roi", "endpoints", "findings", "competition",
    "freshness", "surfaces", "vectors",
}

EXPECTED_ENDPOINT_FIELDS = {
    "id", "targetId", "path", "method", "risk", "confidence",
    "vector", "labels", "signals", "attackSurface", "actionable",
}

EXPECTED_FINDING_FIELDS = {
    "id", "targetId", "endpointId", "title", "severity",
    "confidence", "status", "payout", "risk", "vector",
}

EXPECTED_EVIDENCE_FIELDS = {
    "id", "verdictId", "findingId", "requestUrl",
    "responseStatus", "consistent",
}


# ── Anti-snake check: no snake_case fields in DTOs ────────────────────

def _has_snake_case(key: str) -> bool:
    return "_" in key


def test_target_dto_contract():
    from core_engines.contracts.normalizers import normalize_target

    # Test with empty input
    result = normalize_target(None)
    assert isinstance(result, dict), "normalize_target should return dict"
    assert result["id"] == 0
    assert result["payout"] == 0
    assert result["score"] == 0.0

    # Test with partial input
    result = normalize_target({"id": 1, "name": "Test", "estimated_payout": None})
    assert result["id"] == 1
    assert result["name"] == "Test"
    assert result["payout"] == 0  # None → 0

    # Test field mapping
    result = normalize_target({
        "id": 1, "name": "Test", "domain": "example.com",
        "estimated_payout": 5000, "opportunity_score": 8.5,
        "risk_score": 3.2, "roi": 12.5, "endpoint_count": 10,
        "finding_count": 5, "confirmed_findings": 2,
        "competition_score": 0.7, "freshness_score": 0.9,
    })
    assert result["payout"] == 5000
    assert result["score"] == 8.5
    assert result["risk"] == 3.2
    assert result["endpoints"] == 10
    assert result["findings"] == 5
    assert result["confirmedFindings"] == 2

    # No missing fields
    actual_keys = set(result.keys()) & EXPECTED_TARGET_FIELDS
    missing = EXPECTED_TARGET_FIELDS - actual_keys
    assert not missing, f"Missing fields in target: {missing}"

    # No snake_case
    snake = [k for k in result if _has_snake_case(k)]
    assert not snake, f"snake_case fields in target DTO: {snake}"


def test_opportunity_dto_contract():
    from core_engines.contracts.normalizers import normalize_opportunity

    result = normalize_opportunity(None)
    assert result["payout"] == 0
    assert result["surfaces"] == []
    assert result["vectors"] == []

    result = normalize_opportunity({
        "id": 1, "target_id": 42, "name": "Test", "domain": "example.com",
        "estimated_payout": 10000, "opportunity_score": 9.0,
        "roi": 15.0, "endpoint_count": 20, "finding_count": 8,
        "competition_score": 0.5, "freshness_score": 0.8,
        "surfaces": ["admin"], "vectors": ["sql_injection"],
    })
    assert result["targetId"] == 42
    assert result["payout"] == 10000
    assert result["score"] == 9.0
    assert result["endpoints"] == 20
    assert result["findings"] == 8

    actual_keys = set(result.keys()) & EXPECTED_OPPORTUNITY_FIELDS
    missing = EXPECTED_OPPORTUNITY_FIELDS - actual_keys
    assert not missing, f"Missing fields in opportunity: {missing}"

    snake = [k for k in result if _has_snake_case(k)]
    assert not snake, f"snake_case fields in opportunity DTO: {snake}"


def test_endpoint_dto_contract():
    from core_engines.contracts.normalizers import normalize_endpoint

    result = normalize_endpoint(None)
    assert result["risk"] == 0.0
    assert result["labels"] == []
    assert result["actionable"] is False

    result = normalize_endpoint({
        "id": 1, "target_id": 42, "path": "/api/login", "method": "POST",
        "risk_score": 8.5, "confidence": 0.95, "vector": "sqli",
        "labels": ["auth"], "signals": ["high_risk"],
        "attack_surface": ["login_page"], "actionable": True,
    })
    assert result["targetId"] == 42
    assert result["risk"] == 8.5
    assert result["attackSurface"] == ["login_page"]

    actual_keys = set(result.keys()) & EXPECTED_ENDPOINT_FIELDS
    missing = EXPECTED_ENDPOINT_FIELDS - actual_keys
    assert not missing, f"Missing fields in endpoint: {missing}"

    snake = [k for k in result if _has_snake_case(k)]
    assert not snake, f"snake_case fields in endpoint DTO: {snake}"


def test_finding_dto_contract():
    from core_engines.contracts.normalizers import normalize_finding

    result = normalize_finding(None)
    assert result["payout"] == 0
    assert result["status"] == "open"

    result = normalize_finding({
        "id": 1, "target_id": 42, "endpoint_id": 7,
        "title": "SQL Injection", "severity": "critical",
        "confidence": 0.98, "status": "confirmed",
        "estimated_payout": 5000, "risk_score": 9.0,
        "vector": "sqli",
    })
    assert result["targetId"] == 42
    assert result["payout"] == 5000
    assert result["risk"] == 9.0

    actual_keys = set(result.keys()) & EXPECTED_FINDING_FIELDS
    missing = EXPECTED_FINDING_FIELDS - actual_keys
    assert not missing, f"Missing fields in finding: {missing}"

    snake = [k for k in result if _has_snake_case(k)]
    assert not snake, f"snake_case fields in finding DTO: {snake}"


def test_evidence_dto_contract():
    from core_engines.contracts.normalizers import normalize_evidence

    result = normalize_evidence(None)
    assert result["consistent"] is False

    result = normalize_evidence({
        "id": 1, "verdict_id": 42, "finding_id": 7,
        "request_url": "https://example.com/admin",
        "response_status": 200, "consistent": True,
    })
    assert result["verdictId"] == 42
    assert result["findingId"] == 7
    assert result["requestUrl"] == "https://example.com/admin"
    assert result["consistent"] is True

    actual_keys = set(result.keys()) & EXPECTED_EVIDENCE_FIELDS
    missing = EXPECTED_EVIDENCE_FIELDS - actual_keys
    assert not missing, f"Missing fields in evidence: {missing}"

    snake = [k for k in result if _has_snake_case(k)]
    assert not snake, f"snake_case fields in evidence DTO: {snake}"


def test_paginated_wrapper():
    from core_engines.contracts.wrapper import wrap_paginated, unwrap_items, unwrap_meta

    wrapped = wrap_paginated([{"id": 1}], 1, 0, 10)
    assert wrapped == {"items": [{"id": 1}], "meta": {"total": 1, "skip": 0, "limit": 10}}

    items = unwrap_items(wrapped)
    assert items == [{"id": 1}]

    meta = unwrap_meta(wrapped)
    assert meta == {"total": 1, "skip": 0, "limit": 10}


def test_validation_contract():
    from core_engines.contracts.validator import validate_contract, EXPECTED_FIELDS

    assert "target" in EXPECTED_FIELDS
    assert "opportunity" in EXPECTED_FIELDS
    assert "endpoint" in EXPECTED_FIELDS
    assert "finding" in EXPECTED_FIELDS
    assert "evidence" in EXPECTED_FIELDS

    valid, issues = validate_contract("target", {"id": 1, "name": "test"})
    assert not valid
    assert any("Missing" in i for i in issues)

    valid, issues = validate_contract("target", {
        "id": 1, "name": "test", "domain": "x",
        "payout": 100, "score": 5.0, "risk": 2.0,
        "roi": 10.0, "endpoints": 5, "findings": 3,
        "confirmedFindings": 1, "competition": 0.5, "freshness": 0.8,
    })
    assert valid, f"Target contract should be valid: {issues}"


def test_normalized_paginated():
    from core_engines.contracts.normalizers import normalize_paginated, normalize_target

    raw = {
        "items": [
            {"id": 1, "name": "A", "estimated_payout": 100, "opportunity_score": 5.0, "risk_score": 1.0, "roi": 10.0, "endpoint_count": 5, "finding_count": 3, "confirmed_findings": 1, "competition_score": 0.5, "freshness_score": 0.8},
        ],
        "total": 1,
        "skip": 0,
        "limit": 100,
    }
    result = normalize_paginated(raw, normalize_target)
    assert result["items"][0]["payout"] == 100
    assert result["items"][0]["score"] == 5.0
    assert result["meta"]["total"] == 1
    assert result["meta"]["skip"] == 0
    assert result["meta"]["limit"] == 100
