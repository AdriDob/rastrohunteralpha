#!/usr/bin/env python3
"""Pre-build validation script. Run before production builds.

Usage:
    python scripts/prebuild.py

Exits with code 0 if all checks pass, 1 otherwise.
"""

import importlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CHECKS_PASSED = 0
CHECKS_FAILED = 0


def check(description: str, condition: bool, detail: str = ""):
    global CHECKS_PASSED, CHECKS_FAILED
    if condition:
        CHECKS_PASSED += 1
        print(f"  ✓ {description}")
    else:
        CHECKS_FAILED += 1
        print(f"  ✗ {description}: {detail}")


def main():
    print(f"\n{'='*50}")
    print("  Rastro Pre-Build Validation")
    print(f"{'='*50}\n")

    # === Phase 1: Python dependencies ===
    print("── Python dependencies ──")
    for mod in ["fastapi", "uvicorn", "sqlalchemy", "pydantic", "httpx", "pytest"]:
        try:
            importlib.import_module(mod)
            check(f"{mod} available", True)
        except ImportError:
            check(f"{mod} available", False, "not installed")

    # === Phase 2: Recon tools ===
    print("\n── Recon tools ──")
    from core.recon.tools import _resolve_tool, check_tool_available

    for tool in ["subfinder", "katana", "httpx"]:
        resolved = _resolve_tool(tool)
        check(
            f"{tool} installed",
            bool(resolved),
            f"not found. Install: go install github.com/projectdiscovery/{tool}/cmd/{tool}@latest",
        )
        if resolved:
            check(f"{tool} is Go binary", "go/bin" in resolved, f"resolved to {resolved}")

    # === Phase 3: DB connectivity ===
    print("\n── Database ──")
    try:
        _orig_db_url = os.environ.pop("DATABASE_URL", None)
        from database import db, models
        db.init_db()
        session = db.SessionLocal()
        from sqlalchemy import text
        session.execute(text("SELECT 1"))
        session.close()
        check("Database connection", True)
    except Exception as e:
        check("Database connection", False, str(e))
    finally:
        if _orig_db_url is not None:
            os.environ["DATABASE_URL"] = _orig_db_url
        elif "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

    # === Phase 4: App import ===
    print("\n── Application ──")
    try:
        from api.main import app
        routes = len(app.routes)
        check(f"App loads ({routes} routes)", True)
    except Exception as e:
        check("App loads", False, str(e))

    # === Phase 5: Frontend build ===
    print("\n── Frontend ──")
    frontend_dir = ROOT / "frontend"
    if frontend_dir.is_dir():
        try:
            result = subprocess.run(
                ["npx", "vite", "build"],
                cwd=str(frontend_dir),
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                check("Frontend builds", True)
            else:
                check("Frontend builds", False, result.stderr[-200:])
        except subprocess.TimeoutExpired:
            check("Frontend builds", False, "timed out (120s)")
        except FileNotFoundError:
            check("Frontend builds", False, "npx/node not found")
    else:
        check("Frontend directory exists", False, f"{frontend_dir} not found")

    # === Phase 6: Test suite ===
    print("\n── Test suite ──")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--ignore=tests/test_desktop_release.py", "--tb=short", "-q"],
            cwd=str(ROOT),
            capture_output=True, text=True, timeout=120,
        )
        output = result.stdout or result.stderr or ""
        last_line = output.strip().split("\n")[-1] if output.strip() else ""
        if result.returncode == 0:
            check(f"Tests pass ({last_line})", True)
        else:
            import re
            m = re.search(r'(\d+) passed.*?(\d+) failed', output)
            msg = f"{m.group(0)}" if m else f"exit {result.returncode}"
            check("Tests pass", False, msg)
    except subprocess.TimeoutExpired:
        check("Tests pass", False, "timed out (120s)")

    # === Summary ===
    print(f"\n{'='*50}")
    status = "PASSED" if CHECKS_FAILED == 0 else "FAILED"
    print(f"  {status}: {CHECKS_PASSED} passed, {CHECKS_FAILED} failed")
    print(f"{'='*50}\n")
    return 0 if CHECKS_FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
