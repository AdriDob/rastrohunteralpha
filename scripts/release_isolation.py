#!/usr/bin/env python3
"""ORION Release Isolation Pipeline — one command to validate a clean release.

Usage:
    python scripts/release_isolation.py                    # Full pipeline
    python scripts/release_isolation.py --skip-build       # Skip build, test existing
    python scripts/release_isolation.py --skip-smoke       # Skip smoke/portable/installer
    python scripts/release_isolation.py --skip-installer   # Skip NSIS installer
    python scripts/release_isolation.py --ci               # JSON output for CI
    python scripts/release_isolation.py --clean            # Clean build from zero

Phases:
  1. Clean build (frontend + PyInstaller)
  2. Import audit (0 issues required)
  3. Asset validation (all checks pass)
  4. Smoke test (Windows only — validates EXE)
  5. Portable test (Windows only — temp isolation)
  6. Installer test (Windows only — install/uninstall)
  7. Generate RELEASE_REPORT.md

Exit code: 0 = all pass, 1 = any failure
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
RELEASE_DIR = BUILD_DIR / "release"
REPORT_PATH = PROJECT_ROOT / "RELEASE_REPORT.md"

IS_WINDOWS = sys.platform == "win32"

PASS = True
RESULTS: list[dict] = []


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def step(name: str, func, *args, **kwargs) -> bool:
    global PASS
    log(f"=== {name} ===")
    try:
        ok = func(*args, **kwargs)
        status = "PASS" if ok else "FAIL"
        RESULTS.append({"step": name, "status": status})
        log(f"  → {status}")
        if not ok:
            PASS = False
        return ok
    except Exception as e:
        log(f"  → EXCEPTION: {e}")
        RESULTS.append({"step": name, "status": "ERROR", "detail": str(e)})
        PASS = False
        return False


def run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 300) -> bool:
    try:
        result = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, capture_output=True, text=True, timeout=timeout)
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                log(f"  | {line}")
        if result.stderr:
            for line in result.stderr.strip().split("\n")[-10:]:
                log(f"  ! {line}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log(f"  ! TIMEOUT after {timeout}s")
        return False
    except FileNotFoundError as e:
        log(f"  ! NOT FOUND: {e}")
        return False


def read_version() -> str:
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return "1.6.0"


# ── Phase 1: Clean build ─────────────────────────────────────────────

def phase_clean() -> bool:
    for d in [DIST_DIR, BUILD_DIR]:
        if d.exists():
            shutil.rmtree(d)
            log(f"  Removed: {d}")
    # Also clean PyInstaller caches
    for cache_dir in PROJECT_ROOT.rglob("__pycache__"):
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)
    log("  Clean complete")
    return True


def phase_build() -> bool:
    log("  Running build_release.py...")
    cmd = [sys.executable, str(SCRIPT_DIR / "build_release.py"), "--no-nsis"]
    return run_cmd(cmd, timeout=600)


def phase_build_full() -> bool:
    """Windows build with NSIS installer."""
    log("  Running build_release.py (full)...")
    cmd = [sys.executable, str(SCRIPT_DIR / "build_release.py")]
    return run_cmd(cmd, timeout=600)


# ── Phase 2: Import audit ───────────────────────────────────────────

def phase_import_audit() -> bool:
    log("  Running audit_imports.py...")
    return run_cmd([sys.executable, str(SCRIPT_DIR / "audit_imports.py")], timeout=120)


# ── Phase 3: Asset validation ───────────────────────────────────────

def phase_asset_validation() -> bool:
    log("  Running validate_assets.py...")
    return run_cmd([sys.executable, str(SCRIPT_DIR / "validate_assets.py")], timeout=120)


# ── Phase 4: Smoke test ─────────────────────────────────────────────

def phase_smoke_test() -> bool:
    log("  Running smoke_test.py...")
    return run_cmd([sys.executable, str(SCRIPT_DIR / "smoke_test.py")], timeout=120)


# ── Phase 5: Portable test ──────────────────────────────────────────

def phase_portable_test() -> bool:
    log("  Running test_portable.py...")
    return run_cmd([sys.executable, str(SCRIPT_DIR / "test_portable.py")], timeout=180)


# ── Phase 6: Installer test ─────────────────────────────────────────

def phase_installer_test() -> bool:
    log("  Running test_installer.py...")
    return run_cmd([sys.executable, str(SCRIPT_DIR / "test_installer.py")], timeout=180)


# ── Phase 7: Generate RELEASE_REPORT.md ─────────────────────────────

def generate_report(version: str, artifacts: dict[str, str] | None = None) -> bool:
    log(f"  Generating {REPORT_PATH}...")
    cmd = [sys.executable, str(SCRIPT_DIR / "generate_release_report.py")]
    return run_cmd(cmd, timeout=60)


# ── Main ────────────────────────────────────────────────────────────

def main() -> None:
    global PASS
    parser = argparse.ArgumentParser(description="ORION Release Isolation Pipeline")
    parser.add_argument("--skip-build", action="store_true", help="Skip build, test existing")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip smoke/portable/installer tests")
    parser.add_argument("--skip-installer", action="store_true", help="Skip NSIS installer build")
    parser.add_argument("--clean", action="store_true", help="Clean build from zero")
    parser.add_argument("--ci", action="store_true", help="JSON output for CI")
    args = parser.parse_args()

    version = read_version()
    log(f"ORION Release Isolation Pipeline v{version}")
    log(f"Platform: {sys.platform}")
    log(f"Windows: {IS_WINDOWS}")
    log("")

    # ── Phase 1: Build ──
    if args.clean:
        step("Clean", phase_clean)

    if not args.skip_build:
        if args.skip_installer or not IS_WINDOWS:
            step("Build (Linux mode)", phase_build)
        else:
            step("Build (Windows mode)", phase_build_full)

    # ── Phase 2: Import audit ──
    step("Import audit", phase_import_audit)

    # ── Phase 3: Asset validation ──
    step("Asset validation", phase_asset_validation)

    # ── Phase 4-6: Windows-only tests ──
    if not args.skip_smoke and IS_WINDOWS:
        step("Smoke test", phase_smoke_test)
        step("Portable test", phase_portable_test)
        step("Installer test", phase_installer_test)
    elif not args.skip_smoke:
        log("  ⚠ Smoke/portable/installer tests skipped — requires Windows")
        RESULTS.append({"step": "Smoke test", "status": "SKIP (not Windows)"})
        RESULTS.append({"step": "Portable test", "status": "SKIP (not Windows)"})
        RESULTS.append({"step": "Installer test", "status": "SKIP (not Windows)"})
    else:
        RESULTS.append({"step": "Smoke test", "status": "SKIP (--skip-smoke)"})
        RESULTS.append({"step": "Portable test", "status": "SKIP (--skip-smoke)"})
        RESULTS.append({"step": "Installer test", "status": "SKIP (--skip-smoke)"})

    # ── Phase 7: Generate report ──
    step("Release report", generate_report, version)

    # ── Summary ──
    log("")
    log("=" * 50)
    log("RELEASE ISOLATION RESULTS")
    log("=" * 50)
    for r in RESULTS:
        icon = "[PASS]" if r["status"] == "PASS" else "[FAIL]" if r["status"] == "FAIL" else "[SKIP]"
        log(f"  {icon} {r['step']}: {r['status']}")
    log("")
    log(f"Overall: {'ALL PASS' if PASS else 'FAILURES DETECTED'}")

    if args.ci:
        print(json.dumps({"success": PASS, "results": RESULTS}, indent=2))

    sys.exit(0 if PASS else 1)


if __name__ == "__main__":
    main()
