"""Shared fixtures for Rastro test suite."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def go_bin() -> Path:
    return Path.home() / "go" / "bin"


@pytest.fixture
def recon_tools(go_bin: Path) -> dict[str, Path | None]:
    """Resolve all recon tool paths."""
    from core.recon.tools import _resolve_tool
    return {
        "subfinder": _resolve_tool("subfinder"),
        "katana": _resolve_tool("katana"),
        "httpx": _resolve_tool("httpx"),
    }
