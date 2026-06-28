"""API versioning and migration support.

Current: 1.0
"""

from __future__ import annotations

API_VERSION = "1.0"
API_SCHEMA = "rastro/v1"

VERSIONS: dict[str, int] = {
    "1.0": 1,
}

# Routes grouped by API version
VERSIONED_PREFIXES: dict[str, list[str]] = {
    "1.0": [
        "/api/health",
        "/api/version",
        "/api/targets",
        "/api/endpoints",
        "/api/findings",
        "/api/evidence",
        "/api/opportunities",
        "/api/opportunity",
        "/api/reports",
        "/api/hypotheses",
        "/api/pipeline",
        "/api/quick-wins",
        "/api/assistant",
        "/api/intelligence",
        "/api/operations",
        "/api/system",
        "/api/auth",
        "/api/sync",
        "/api/mobile",
    ],
}


def is_version_supported(version: str) -> bool:
    return version in VERSIONS


def latest_version() -> str:
    return API_VERSION
