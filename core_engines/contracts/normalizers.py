"""Contract normalizers — convert raw backend dicts to stable frontend DTOs.

Every normalizer:
  - Renames snake_case → camelCase
  - Maps inconsistent fields to canonical names
  - Eliminates null/undefined instability with safe defaults
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ── Field mapping tables ──────────────────────────────────────────────

TARGET_FIELD_MAP: Dict[str, str] = {
    "estimated_payout": "payout",
    "opportunity_score": "score",
    "risk_score": "risk",
    "endpoint_count": "endpoints",
    "finding_count": "findings",
    "confirmed_findings": "confirmedFindings",
    "competition_score": "competition",
    "freshness_score": "freshness",
    "created_at": "createdAt",
    "last_updated": "lastUpdated",
}

OPPORTUNITY_FIELD_MAP: Dict[str, str] = {
    "estimated_payout": "payout",
    "opportunity_score": "score",
    "competition_score": "competition",
    "freshness_score": "freshness",
    "target_id": "targetId",
    "endpoint_count": "endpoints",
    "finding_count": "findings",
    "max_risk": "risk",
    "created_at": "createdAt",
    "last_update": "lastUpdated",
}

ENDPOINT_FIELD_MAP: Dict[str, str] = {
    "target_id": "targetId",
    "risk_score": "risk",
    "created_at": "createdAt",
    "attack_surface": "attackSurface",
}

FINDING_FIELD_MAP: Dict[str, str] = {
    "target_id": "targetId",
    "endpoint_id": "endpointId",
    "estimated_payout": "payout",
    "risk_score": "risk",
    "created_at": "createdAt",
    "confirmed_at": "confirmedAt",
}

EVIDENCE_FIELD_MAP: Dict[str, str] = {
    "verdict_id": "verdictId",
    "finding_id": "findingId",
    "request_url": "requestUrl",
    "response_status": "responseStatus",
    "created_at": "createdAt",
}

OVERVIEW_FIELD_MAP: Dict[str, str] = {
    "target_count": "targets",
    "endpoint_count": "endpoints",
    "finding_count": "findings",
    "confirmed_verdicts": "confirmed",
    "active_scans": "activeScans",
    "high_signal_endpoints": "highSignal",
    "avg_risk_score": "avgRisk",
    "risk_distribution": "riskDistribution",
    "vector_distribution": "vectorDistribution",
    "severity_counts": "severity",
    "pipeline_stages": "pipeline",
}


# ── snake_case → camelCase converter ──────────────────────────────────

def _to_camel(key: str) -> str:
    """Convert snake_case to camelCase."""
    if "_" not in key:
        return key
    parts = key.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


# ── Safe value helpers ────────────────────────────────────────────────

def _safe_int(v: Any, default: int = 0) -> int:
    if v is None:
        return default
    try:
        return int(v)
    except (ValueError, TypeError):
        return default


def _safe_float(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _safe_str(v: Any, default: str = "") -> str:
    if v is None:
        return default
    return str(v)


def _safe_list(v: Any, default: Optional[List] = None) -> List:
    if v is None or not isinstance(v, list):
        return default or []
    return v


def _safe_dict(v: Any, default: Optional[Dict] = None) -> Dict:
    if v is None or not isinstance(v, dict):
        return default or {}
    return v


# ── Normalizers ───────────────────────────────────────────────────────

def _apply_map(raw: Dict[str, Any], field_map: Dict[str, str]) -> Dict[str, Any]:
    """Rename fields using field_map, camelCase the rest."""
    out: Dict[str, Any] = {}
    for key, value in raw.items():
        mapped = field_map.get(key, _to_camel(key))
        out[mapped] = value
    return out


def normalize_target(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize a target dict to stable frontend DTO."""
    if not raw:
        return _empty_target()
    mapped = _apply_map(raw, TARGET_FIELD_MAP)
    # Safe defaults for critical fields
    mapped["payout"] = _safe_int(mapped.get("payout"))
    mapped["score"] = _safe_float(mapped.get("score"))
    mapped["risk"] = _safe_float(mapped.get("risk"))
    mapped["roi"] = _safe_float(mapped.get("roi"))
    mapped["endpoints"] = _safe_int(mapped.get("endpoints"))
    mapped["findings"] = _safe_int(mapped.get("findings"))
    mapped["confirmedFindings"] = _safe_int(mapped.get("confirmedFindings"))
    mapped["competition"] = _safe_float(mapped.get("competition"))
    mapped["freshness"] = _safe_float(mapped.get("freshness"))
    mapped["name"] = _safe_str(mapped.get("name"))
    mapped["domain"] = _safe_str(mapped.get("domain"))
    mapped["id"] = _safe_int(mapped.get("id"))
    return mapped


def normalize_opportunity(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize an opportunity dict to stable frontend DTO."""
    if not raw:
        return _empty_opportunity()
    mapped = _apply_map(raw, OPPORTUNITY_FIELD_MAP)
    mapped["payout"] = _safe_int(mapped.get("payout"))
    mapped["score"] = _safe_float(mapped.get("score"))
    mapped["risk"] = _safe_float(mapped.get("risk"))
    mapped["roi"] = _safe_float(mapped.get("roi"))
    mapped["endpoints"] = _safe_int(mapped.get("endpoints"))
    mapped["findings"] = _safe_int(mapped.get("findings"))
    mapped["competition"] = _safe_float(mapped.get("competition"))
    mapped["freshness"] = _safe_float(mapped.get("freshness"))
    mapped["name"] = _safe_str(mapped.get("name"))
    mapped["domain"] = _safe_str(mapped.get("domain"))
    mapped["targetId"] = _safe_int(mapped.get("targetId"))
    mapped["surfaces"] = _safe_list(mapped.get("surfaces"))
    mapped["vectors"] = _safe_list(mapped.get("vectors"))
    return mapped


def normalize_endpoint(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize an endpoint dict to stable frontend DTO."""
    if not raw:
        return _empty_endpoint()
    mapped = _apply_map(raw, ENDPOINT_FIELD_MAP)
    mapped["risk"] = _safe_float(mapped.get("risk"))
    mapped["confidence"] = _safe_float(mapped.get("confidence"))
    mapped["targetId"] = _safe_int(mapped.get("targetId"))
    mapped["path"] = _safe_str(mapped.get("path"))
    mapped["method"] = _safe_str(mapped.get("method"))
    mapped["vector"] = _safe_str(mapped.get("vector"))
    mapped["labels"] = _safe_list(mapped.get("labels"))
    mapped["signals"] = _safe_list(mapped.get("signals"))
    mapped["attackSurface"] = _safe_list(mapped.get("attackSurface"))
    mapped["actionable"] = bool(mapped.get("actionable"))
    return mapped


def normalize_finding(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize a finding dict to stable frontend DTO."""
    if not raw:
        return _empty_finding()
    mapped = _apply_map(raw, FINDING_FIELD_MAP)
    mapped["payout"] = _safe_int(mapped.get("payout"))
    mapped["risk"] = _safe_float(mapped.get("risk"))
    mapped["confidence"] = _safe_float(mapped.get("confidence"))
    mapped["targetId"] = _safe_int(mapped.get("targetId"))
    mapped["endpointId"] = _safe_int(mapped.get("endpointId"))
    mapped["title"] = _safe_str(mapped.get("title"))
    mapped["severity"] = _safe_str(mapped.get("severity"))
    mapped["status"] = _safe_str(mapped.get("status"))
    mapped["vector"] = _safe_str(mapped.get("vector"))
    return mapped


def normalize_evidence(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize an evidence dict to stable frontend DTO."""
    if not raw:
        return _empty_evidence()
    mapped = _apply_map(raw, EVIDENCE_FIELD_MAP)
    mapped["verdictId"] = _safe_int(mapped.get("verdictId"))
    mapped["findingId"] = _safe_int(mapped.get("findingId"))
    mapped["requestUrl"] = _safe_str(mapped.get("requestUrl"))
    mapped["responseStatus"] = _safe_int(mapped.get("responseStatus"))
    mapped["consistent"] = bool(mapped.get("consistent"))
    return mapped


def normalize_overview(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize overview data to stable frontend shape."""
    if not raw:
        return _empty_overview()
    mapped = _apply_map(raw, OVERVIEW_FIELD_MAP)
    mapped["targets"] = _safe_int(mapped.get("targets"))
    mapped["endpoints"] = _safe_int(mapped.get("endpoints"))
    mapped["findings"] = _safe_int(mapped.get("findings"))
    mapped["confirmed"] = _safe_int(mapped.get("confirmed"))
    mapped["activeScans"] = _safe_int(mapped.get("activeScans"))
    mapped["highSignal"] = _safe_int(mapped.get("highSignal"))
    mapped["avgRisk"] = _safe_float(mapped.get("avgRisk"))
    mapped["riskDistribution"] = _safe_dict(mapped.get("riskDistribution"), {
        "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0,
    })
    mapped["severity"] = _safe_dict(mapped.get("severity"), {
        "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0,
    })
    mapped["pipeline"] = _safe_dict(mapped.get("pipeline"), {
        "detected": 0, "validated": 0, "confirmed": 0, "reported": 0,
    })
    mapped["vectorDistribution"] = _safe_dict(mapped.get("vectorDistribution"))
    # Normalize top targets
    top = mapped.get("topTargets", [])
    if isinstance(top, list):
        mapped["topTargets"] = [normalize_target(t) for t in top]
    else:
        mapped["topTargets"] = []
    return mapped


def normalize_paginated(raw: Dict[str, Any], item_normalizer) -> Dict[str, Any]:
    """Normalize a paginated response {items, total, skip, limit}.

    Returns {items: [...normalized...], meta: {total, skip, limit}}.
    """
    items_raw = _safe_list(raw.get("items"))
    items = [item_normalizer(i) for i in items_raw]
    return {
        "items": items,
        "meta": {
            "total": _safe_int(raw.get("total"), len(items)),
            "skip": _safe_int(raw.get("skip"), 0),
            "limit": _safe_int(raw.get("limit"), 100),
        },
    }


# ── Empty DTO factories (guarantee no undefined/null propagation) ─────

def _empty_target() -> Dict[str, Any]:
    return {
        "id": 0, "name": "", "domain": "", "payout": 0, "score": 0.0,
        "risk": 0.0, "roi": 0.0, "endpoints": 0, "findings": 0,
        "confirmedFindings": 0, "competition": 0.0, "freshness": 0.0,
    }


def _empty_opportunity() -> Dict[str, Any]:
    return {
        "id": 0, "targetId": 0, "name": "", "domain": "", "payout": 0,
        "score": 0.0, "risk": 0.0, "roi": 0.0, "endpoints": 0,
        "findings": 0, "competition": 0.0, "freshness": 0.0,
        "surfaces": [], "vectors": [],
    }


def _empty_endpoint() -> Dict[str, Any]:
    return {
        "id": 0, "targetId": 0, "path": "", "method": "GET",
        "risk": 0.0, "confidence": 0.0, "vector": "",
        "labels": [], "signals": [], "attackSurface": [],
        "actionable": False,
    }


def _empty_finding() -> Dict[str, Any]:
    return {
        "id": 0, "targetId": 0, "endpointId": 0, "title": "",
        "severity": "info", "confidence": 0.0, "status": "open",
        "payout": 0, "risk": 0.0, "vector": "",
    }


def _empty_evidence() -> Dict[str, Any]:
    return {
        "id": 0, "verdictId": 0, "findingId": 0, "requestUrl": "",
        "responseStatus": 0, "consistent": False,
    }


def _empty_overview() -> Dict[str, Any]:
    return {
        "targets": 0, "endpoints": 0, "findings": 0, "confirmed": 0,
        "activeScans": 0, "highSignal": 0, "avgRisk": 0.0,
        "riskDistribution": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        "severity": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        "pipeline": {"detected": 0, "validated": 0, "confirmed": 0, "reported": 0},
        "vectorDistribution": {},
        "topTargets": [],
    }
