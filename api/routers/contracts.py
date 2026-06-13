"""Contract compliance debug/diagnostic endpoint.

GET /api/contracts/debug  — Full contract report
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter

from core.contracts.normalizers import (
    normalize_target,
    normalize_opportunity,
    normalize_endpoint,
    normalize_finding,
    normalize_evidence,
)
from core.contracts.validator import (
    EXPECTED_FIELDS,
    validate_contract,
    validate_paginated_response,
    build_debug_report,
)
from core.contracts.wrapper import wrap_paginated, wrap_list

logger = logging.getLogger("rastro.api.contracts")

router = APIRouter(prefix="/api/contracts", tags=["contracts"])


def _fetch_sample(router_name: str, list_call, normalizer, limit: int = 5) -> Dict[str, Any]:
    """Fetch a sample from a list endpoint and validate it."""
    try:
        raw = list_call(skip=0, limit=limit)
    except Exception as exc:
        return {
            "router": router_name,
            "error": str(exc),
            "sample": [],
            "validation": {"valid": 0, "issues": ["Failed to fetch"]},
        }

    items_raw = raw.get("items", []) if isinstance(raw, dict) else []
    items = [normalizer(i) for i in items_raw]

    validation = validate_paginated_response(raw, router_name)
    return {
        "router": router_name,
        "sample_count": len(items),
        "sample": items[:3],
        "validation": validation,
    }


@router.get("/debug")
async def contracts_debug():
    """Full contract compliance report.

    Shows expected schema vs actual backend response for every contract.
    """
    from core.contracts.validator import build_debug_report

    report = build_debug_report()

    # Test sample data from live endpoints
    samples: List[Dict[str, Any]] = []

    # Targets
    try:
        from api.services.data_service import list_targets
        raw = list_targets(skip=0, limit=5)
        items_raw = raw.get("items", []) if isinstance(raw, dict) else []
        items = [normalize_target(t) for t in items_raw]
        validation = validate_paginated_response(raw, "target")
        samples.append({
            "contract": "target",
            "endpoint": "/api/targets",
            "count": len(items),
            "sample": items[:2],
            "validation": validation,
            "status": "ok" if validation["valid_items"] == validation["total_items"] else "mismatch",
        })
    except Exception as exc:
        samples.append({"contract": "target", "endpoint": "/api/targets", "error": str(exc), "status": "error"})

    # Opportunities
    try:
        from api.services.data_service import list_opportunities
        raw = list_opportunities(skip=0, limit=5)
        items_raw = raw.get("items", []) if isinstance(raw, dict) else []
        items = [normalize_opportunity(o) for o in items_raw]
        validation = validate_paginated_response(raw, "opportunity")
        samples.append({
            "contract": "opportunity",
            "endpoint": "/api/opportunities",
            "count": len(items),
            "sample": items[:2],
            "validation": validation,
            "status": "ok" if validation["valid_items"] == validation["total_items"] else "mismatch",
        })
    except Exception as exc:
        samples.append({"contract": "opportunity", "endpoint": "/api/opportunities", "error": str(exc), "status": "error"})

    # Endpoints
    try:
        from api.services.data_service import list_endpoints
        raw = list_endpoints(skip=0, limit=5)
        items_raw = raw.get("items", []) if isinstance(raw, dict) else []
        items = [normalize_endpoint(e) for e in items_raw]
        validation = validate_paginated_response(raw, "endpoint")
        samples.append({
            "contract": "endpoint",
            "endpoint": "/api/endpoints",
            "count": len(items),
            "sample": items[:2],
            "validation": validation,
            "status": "ok" if validation["valid_items"] == validation["total_items"] else "mismatch",
        })
    except Exception as exc:
        samples.append({"contract": "endpoint", "endpoint": "/api/endpoints", "error": str(exc), "status": "error"})

    # Findings
    try:
        from api.services.data_service import list_findings
        raw = list_findings(skip=0, limit=5)
        items_raw = raw.get("items", []) if isinstance(raw, dict) else []
        items = [normalize_finding(f) for f in items_raw]
        validation = validate_paginated_response(raw, "finding")
        samples.append({
            "contract": "finding",
            "endpoint": "/api/findings",
            "count": len(items),
            "sample": items[:2],
            "validation": validation,
            "status": "ok" if validation["valid_items"] == validation["total_items"] else "mismatch",
        })
    except Exception as exc:
        samples.append({"contract": "finding", "endpoint": "/api/findings", "error": str(exc), "status": "error"})

    # Evidence
    try:
        from api.services.data_service import list_evidence
        raw = list_evidence(skip=0, limit=5)
        items_raw = raw.get("items", []) if isinstance(raw, dict) else []
        items = [normalize_evidence(e) for e in items_raw]
        validation = validate_paginated_response(raw, "evidence")
        samples.append({
            "contract": "evidence",
            "endpoint": "/api/evidence",
            "count": len(items),
            "sample": items[:2],
            "validation": validation,
            "status": "ok" if validation["valid_items"] == validation["total_items"] else "mismatch",
        })
    except Exception as exc:
        samples.append({"contract": "evidence", "endpoint": "/api/evidence", "error": str(exc), "status": "error"})

    report["live_samples"] = samples
    report["summary"] = {
        "contracts_checked": len(samples),
        "ok": sum(1 for s in samples if s.get("status") == "ok"),
        "mismatch": sum(1 for s in samples if s.get("status") == "mismatch"),
        "errors": sum(1 for s in samples if s.get("status") == "error"),
    }

    return report
