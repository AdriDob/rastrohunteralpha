"""
Tool availability checking and version detection for recon tools.
"""

import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger("rastro.recon.tools")

_GO_BIN_ENV = os.environ.get("GOPATH", str(Path.home() / "go"))
GO_BIN = Path(_GO_BIN_ENV) / "bin"

# Tools installed via `go install ...` — prefer go bin path
GO_TOOLS = {"httpx", "katana", "subfinder", "waybackurls", "gau"}


def _resolve_tool(tool_name: str) -> str | None:
    """Resolve tool path, preferring Go-installed binaries over system PATH."""
    if tool_name in GO_TOOLS:
        go_path = GO_BIN / tool_name
        if go_path.is_file():
            return str(go_path)
    return shutil.which(tool_name)

# Map of tool names to CLI commands for version checking
TOOL_CHECKS = {
    "subfinder": ["subfinder", "-version"],
    "katana": ["katana", "-version"],
    "httpx": ["httpx", "-version"],
    "waybackurls": ["waybackurls", "-h"],
    "nuclei": ["nuclei", "-version"],
    "gau": ["gau", "--version"],
    "ffuf": ["ffuf", "-V"],
    "whois": ["whois", "--version"],
}

CRITICAL_TOOLS = ["subfinder", "katana", "httpx"]
OPTIONAL_TOOLS = ["waybackurls", "nuclei", "gau", "ffuf", "whois"]


def check_tool_available(tool_name: str) -> bool:
    """Check if a CLI tool is available, preferring Go-installed binaries."""
    return _resolve_tool(tool_name) is not None


async def check_tool_async(
    tool_name: str, test_cmd: List[str], timeout: int = 5
) -> bool:
    """
    Async check if a tool responds to a version/help command.
    Returns True if tool is available and responds within timeout.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *test_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            # Tool exists if it responds without crashing
            return True
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return False
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.warning(f"Error checking tool {tool_name}: {e}")
        return False


async def verify_recon_tools(mode: str = "FAST") -> Dict[str, bool]:
    """
    Verify availability of required recon tools for the given mode.

    Returns dict of {tool_name: available_bool}
    Logs warnings for missing critical tools.
    """
    status = {}

    # Check critical tools first
    for tool in CRITICAL_TOOLS:
        available = check_tool_available(tool)
        status[tool] = available
        if not available:
            logger.warning(f"Critical tool '{tool}' not found in PATH")
        else:
            logger.info(f"Tool '{tool}' found at {shutil.which(tool)}")

    # Check optional tools
    for tool in OPTIONAL_TOOLS:
        available = check_tool_available(tool)
        status[tool] = available
        if available:
            logger.info(f"Optional tool '{tool}' available")

    # For DEEP/API modes, httpx is mandatory
    if mode.upper() in {"DEEP", "API"} and not status.get("httpx"):
        logger.warning("DEEP/API mode requested but 'httpx' not available")

    return status


def validate_mode_compatibility(
    mode: str, tool_status: Dict[str, bool]
) -> tuple[bool, str]:
    """
    Check if requested recon mode is compatible with available tools.

    Returns (is_compatible, reason_if_not)
    """
    mode_upper = mode.upper()

    # FAST mode only needs subfinder, katana
    if mode_upper == "FAST":
        if not tool_status.get("subfinder") or not tool_status.get("katana"):
            return False, "FAST mode requires subfinder and katana"
        return True, ""

    # DEEP mode needs everything except nuclei
    if mode_upper == "DEEP":
        required = ["subfinder", "katana", "httpx"]
        missing = [t for t in required if not tool_status.get(t)]
        if missing:
            return False, f"DEEP mode requires: {', '.join(missing)}"
        return True, ""

    # API mode needs everything
    if mode_upper == "API":
        required = ["subfinder", "katana", "httpx"]
        missing = [t for t in required if not tool_status.get(t)]
        if missing:
            return False, f"API mode requires: {', '.join(missing)}"
        return True, ""

    return False, f"Unknown recon mode: {mode}"
