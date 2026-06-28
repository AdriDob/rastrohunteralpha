"""Shared fixtures for Rastro test suite."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

# ── Path fixtures ─────────────────────────────────────────────────


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def go_bin() -> Path:
    return Path.home() / "go" / "bin"


@pytest.fixture
def recon_tools(go_bin: Path) -> dict[str, Path | None]:
    """Resolve all recon tool paths."""
    from core_engines.recon.tools import _resolve_tool
    return {
        "subfinder": _resolve_tool("subfinder"),
        "katana": _resolve_tool("katana"),
        "httpx": _resolve_tool("httpx"),
    }


# ── Test data factories ───────────────────────────────────────────


@pytest.fixture
def target_factory() -> dict[str, Any]:
    """Create a minimal target payload."""
    return {
        "name": "test-target.example.com",
        "domain": "example.com",
    }


@pytest.fixture
def endpoint_factory() -> dict[str, Any]:
    """Create a minimal endpoint payload."""
    return {
        "path": "/api/test",
        "method": "GET",
        "params": {},
    }


@pytest.fixture
def finding_factory() -> dict[str, Any]:
    """Create a minimal finding payload."""
    return {
        "vulnerability_type": "information_disclosure",
        "severity": "medium",
        "description": "Test finding description",
    }


@pytest.fixture
def report_factory() -> dict[str, Any]:
    """Create a minimal report payload."""
    return {
        "format": "hackerone_json",
        "severity": "medium",
        "vulnerability": "information_disclosure",
    }


@pytest.fixture
def verdict_factory() -> dict[str, Any]:
    """Create a confirmed verdict payload."""
    return {
        "hot_path_id": "0:endpoint:GET:/api/test",
        "status": "confirmed",
        "confidence": 0.85,
        "reason": "Test verdict reason",
    }


@pytest.fixture
def evidence_factory() -> dict[str, Any]:
    """Create a minimal evidence entry."""
    return {
        "type": "request_response",
        "request": "GET /api/test HTTP/1.1",
        "response": "HTTP/1.1 200 OK",
        "signals": ["test_signal"],
    }


@pytest.fixture
def scan_context_factory() -> dict[str, Any]:
    """Create a full scan context for pipeline testing."""
    return {
        "target_id": 1,
        "target_name": "test-target.example.com",
        "baseline_token": None,
        "probe_token": None,
        "endpoints": [
            {"path": "/api/users", "method": "GET", "params": {"id": "1"}},
            {"path": "/api/admin", "method": "POST", "params": {"action": "delete"}},
            {"path": "/api/data", "method": "GET", "params": {}},
        ],
    }
