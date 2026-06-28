"""Tests for recon tool resolution and runner integration."""

from __future__ import annotations

import subprocess
from pathlib import Path


class TestToolResolution:
    """Verify that recon tools resolve to the correct Go-installed binaries."""

    def test_go_bin_in_path(self):
        go_bin = Path.home() / "go" / "bin"
        assert go_bin.is_dir(), f"Go bin directory not found: {go_bin}"

    def test_httpx_resolves_to_go_binary(self):
        from core_engines.recon.tools import _resolve_tool
        resolved = _resolve_tool("httpx")
        assert resolved is not None, "httpx not found"
        go_bin = Path.home() / "go" / "bin" / "httpx"
        assert Path(resolved) == go_bin, (
            f"httpx resolved to {resolved}, expected {go_bin}"
        )

    def test_katana_resolves_to_go_binary(self):
        from core_engines.recon.tools import _resolve_tool
        resolved = _resolve_tool("katana")
        assert resolved is not None, "katana not found"
        go_bin = Path.home() / "go" / "bin" / "katana"
        assert Path(resolved) == go_bin

    def test_subfinder_resolves_to_go_binary(self):
        from core_engines.recon.tools import _resolve_tool
        resolved = _resolve_tool("subfinder")
        assert resolved is not None, "subfinder not found"
        go_bin = Path.home() / "go" / "bin" / "subfinder"
        assert Path(resolved) == go_bin

    def test_check_tool_available(self):
        from core_engines.recon.tools import check_tool_available
        assert check_tool_available("subfinder") is True
        assert check_tool_available("katana") is True
        assert check_tool_available("httpx") is True

    def test_go_httpx_version(self):
        """Verify the Go httpx responds (vs Python httpx which has different CLI)."""
        from core_engines.recon.tools import _resolve_tool
        binary = _resolve_tool("httpx")
        result = subprocess.run(
            [binary, "-version"], capture_output=True, text=True, timeout=10
        )
        output = (result.stdout + result.stderr).lower()
        assert "httpx" in output or "projectdiscovery" in output or "version" in output

    def test_katana_version(self):
        from core_engines.recon.tools import _resolve_tool
        binary = _resolve_tool("katana")
        result = subprocess.run(
            [binary, "-version"], capture_output=True, text=True, timeout=10
        )
        output = (result.stdout + result.stderr).lower()
        assert "katana" in output or "projectdiscovery" in output


class TestRunnerIntegration:
    """Verify runner classes can instantiate with resolved binaries."""

    def test_runner_instantiation(self):
        from pathlib import Path

        from core_engines.recon.runner import ReconRunner
        runner = ReconRunner(Path("/tmp/test-runner"))
        assert runner.subfinder._binary is not None
        assert runner.katana._binary is not None
        assert runner.httpx._binary is not None
        assert "go/bin" in runner.subfinder._binary
        assert "go/bin" in runner.katana._binary
        assert "go/bin" in runner.httpx._binary

    def test_tools_module_import(self):
        from core_engines.recon.tools import (
            CRITICAL_TOOLS,
        )
        assert "subfinder" in CRITICAL_TOOLS
        assert "katana" in CRITICAL_TOOLS
        assert "httpx" in CRITICAL_TOOLS
