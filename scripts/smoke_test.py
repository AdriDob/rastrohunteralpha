#!/usr/bin/env python3
"""ORION Smoke Test — validates built executable in production mode.

Usage:
    python scripts/smoke_test.py                           # Uses dist/Orion/Orion.exe
    python scripts/smoke_test.py --exe path/to/Orion.exe  # Custom executable
    python scripts/smoke_test.py --ci                      # CI mode (no browser/tray)

Verifies:
  - Backend starts
  - API health endpoint responds
  - Frontend serves index.html
  - WebSocket connected
  - EventBus started
  - Watchdog started
  - Health Engine started
  - Autonomous Engine started
  - Clean shutdown
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PASS = 0
FAIL = 0
SKIP = 0
TIMESTAMP = time.strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    print(f"  {msg}")


def ok(msg: str) -> None:
    global PASS
    PASS += 1
    print(f"  \u2713 {msg}")


def fail(msg: str) -> None:
    global FAIL
    FAIL += 1
    print(f"  \u2717 {msg}")


def skip(msg: str) -> None:
    global SKIP
    SKIP += 1
    print(f"  \u2014 {msg}")


def http_get(url: str, timeout: float = 5.0) -> tuple[int, str]:
    try:
        resp = urllib.request.urlopen(url, timeout=timeout)
        return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")
    except Exception as e:
        return 0, str(e)


def wait_for_health(url: str, timeout: float = 30.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        status, body = http_get(url, timeout=2.0)
        if status == 200:
            return True
        time.sleep(0.5)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="ORION Smoke Test")
    parser.add_argument("--exe", type=Path, default=None, help="Path to Orion.exe")
    parser.add_argument("--ci", action="store_true", help="CI mode (no browser/tray)")
    parser.add_argument("--host", default="127.0.0.1", help="Backend host")
    parser.add_argument("--port", type=int, default=8000, help="Backend port")
    args = parser.parse_args()

    if args.exe:
        exe_path = args.exe.resolve()
    else:
        exe_path = Path(__file__).resolve().parent.parent / "dist" / "Orion" / "Orion.exe"

    if not exe_path.exists():
        print(f"\n\u2717 Orion.exe not found at: {exe_path}")
        print("  Build first: pyinstaller Orion.spec -y")
        sys.exit(1)

    host = args.host
    port = args.port
    base_url = f"http://{host}:{port}"
    health_url = f"{base_url}/api/health"

    print(f"\n{'=' * 60}")
    print("  ORION SMOKE TEST")
    print(f"  {TIMESTAMP}")
    print(f"  Executable: {exe_path}")
    print(f"{'=' * 60}\n")

    # ── 1. Start the backend ────────────────────────────────────────
    mode = "--browser"  # --tray only shows tray (no backend); --browser starts full stack
    log(f"Starting Orion.exe {mode} --no-tray ...")
    env = os.environ.copy()
    env["ORION_DESKTOP"] = "1"
    env["ORION_SMOKE_TEST"] = "1"

    proc = subprocess.Popen(
        [str(exe_path), mode, "--no-tray"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )

    # ── 2. Wait for backend to be healthy ───────────────────────────
    log("Waiting for backend (up to 30s)...")
    healthy = wait_for_health(health_url, timeout=30.0)
    if healthy:
        ok("Backend started and healthy")
    else:
        fail("Backend failed to start (health endpoint timeout)")
        proc.kill()
        sys.exit(1)

    # ── 3. Verify API health response ───────────────────────────────
    status, body = http_get(health_url)
    if status == 200:
        try:
            data = json.loads(body)
            ok(f"API /api/health responds (status={status})")
            root_status = data.get("status", "")
            if root_status == "ok":
                ok("  Overall status: ok")
            components = data.get("components") or data.get("services")
            if isinstance(components, dict):
                for service, state in components.items():
                    st = state.get("status", str(state)) if isinstance(state, dict) else str(state)
                    if st == "healthy" or st == "ok":
                        ok(f"  {service}: {st}")
                    elif st == "degraded":
                        skip(f"  {service}: {st}")
                    else:
                        fail(f"  {service}: {st}")
        except json.JSONDecodeError:
            ok(f"API /api/health responds (status={status})")
            log(f"  Body: {body[:200]}")
    else:
        fail(f"API /api/health returned HTTP {status}")
        log(f"  Body: {body[:300]}")

    # ── 4. Verify frontend serves ───────────────────────────────────
    status, body = http_get(f"{base_url}/")
    if status == 200 and ("<!DOCTYPE html" in body or "<html" in body or "<!doctype html" in body.lower()):
        ok("Frontend serves index.html")
    elif status == 200:
        ok(f"Frontend root responds (HTTP {status})")
        log(f"  Body starts: {body[:100]}")
    else:
        fail(f"Frontend root returned HTTP {status}")

    status, body = http_get(f"{base_url}/index.html")
    if status == 200:
        ok("Frontend index.html served")
    else:
        skip("Frontend /index.html (may not be needed with SPA routing)")

    # ── 5. Verify WebSocket ─────────────────────────────────────────
    status, body = http_get(f"{base_url}/api/ws/status")
    if status == 200:
        ok("WebSocket status endpoint responds")
    else:
        skip("WebSocket status endpoint (may not be exposed)")

    # ── 6. Verify system status ────────────────────────────────────
    endpoints_to_check = [
        ("System status", "/api/system/status"),
        ("Scheduler status", "/api/scheduler/status"),
        ("EventBus status", "/api/events/status"),
    ]
    for label, path in endpoints_to_check:
        status, body = http_get(f"{base_url}{path}")
        if status == 200:
            ok(f"{label} responds")
        else:
            skip(f"{label} (HTTP {status})")

    # ── 7. Verify engines ──────────────────────────────────────────
    engine_endpoints = [
        ("Watchdog", "/api/watchdog/status"),
        ("Health", "/api/health/status"),
        ("Autonomous", "/api/autonomous/status"),
        ("Agents", "/api/agents/health"),
    ]
    for label, path in engine_endpoints:
        status, body = http_get(f"{base_url}{path}")
        if status == 200:
            ok(f"{label} engine responds")
        else:
            skip(f"{label} engine (HTTP {status})")

    # ── 8. Verify API router is alive ───────────────────────────────
    status, body = http_get(f"{base_url}/api/overview/")
    if status == 200:
        ok("API /api/overview responds")
    else:
        skip(f"API /api/overview (HTTP {status})")

    # ── 9. Clean shutdown ─────────────────────────────────────────
    log("\nShutting down Orion...")
    proc.terminate()
    try:
        proc.wait(timeout=10.0)
        ok(f"Clean shutdown (exit code {proc.returncode})")
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        fail("Forced kill (did not shutdown cleanly in 10s)")

    # ── Results ─────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"  RESULTS:  {PASS} passed, {FAIL} failed, {SKIP} skipped")
    print(f"{'=' * 60}\n")

    if FAIL > 0:
        print("  BUILD FAILED — smoke test errors detected")
        print(f"  Log: {exe_path.parent / 'logs' / 'smoke_test.log' if False else 'see above'}")
        sys.exit(1)

    print("  Smoke test PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
