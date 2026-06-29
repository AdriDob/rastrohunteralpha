#!/usr/bin/env python3
"""ORION Portable Test — validates that the portable build runs outside the repo.

Copies the Portable folder (dist/Orion/) to a temp directory outside the repo,
then runs smoke test against it.

Usage:
    python scripts/test_portable.py
    python scripts/test_portable.py --source path/to/Orion
    python scripts/test_portable.py --keep-temp
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

PASS = 0
FAIL = 0


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
    parser = argparse.ArgumentParser(description="ORION Portable Test")
    parser.add_argument("--source", type=Path, default=None, help="Path to Orion directory")
    parser.add_argument("--keep-temp", action="store_true", help="Keep temp directory after test")
    args = parser.parse_args()

    if args.source:
        orion_dir = args.source.resolve()
    else:
        orion_dir = Path(__file__).resolve().parent.parent / "dist" / "Orion"

    if not orion_dir.is_dir():
        print(f"\n\u2717 Orion directory not found at: {orion_dir}")
        print("  Build first: pyinstaller Orion.spec -y")
        sys.exit(1)

    orion_exe = orion_dir / "Orion.exe"
    if not orion_exe.exists():
        print(f"\n\u2717 Orion.exe not found in {orion_dir}")
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print("  ORION PORTABLE TEST")
    print(f"  Source: {orion_dir}")
    print(f"{'=' * 60}\n")

    log("Checking critical files...")
    required_files = [
        "Orion.exe",
        "_internal/frontend_dist/index.html",
    ]
    for f in required_files:
        if f and (orion_dir / f).exists():
            ok(f"  {f} exists")
        elif f:
            fail(f"  {f} missing")

    # Create temp directory OUTSIDE the repo
    temp_dir = Path(tempfile.mkdtemp(prefix="orion_portable_"))
    portable_dir = temp_dir / "Orion"
    log(f"Copying to temp location: {portable_dir}")
    log("  (simulating user extracting Portable/Orion.zip to Desktop)")

    try:
        shutil.copytree(orion_dir, portable_dir)
    except Exception as e:
        fail(f"Copy failed: {e}")
        shutil.rmtree(temp_dir)
        sys.exit(1)

    portable_exe = portable_dir / "Orion.exe"
    if portable_exe.exists():
        ok(f"Copied to {portable_dir}")
    else:
        fail("Copy failed — Orion.exe not found in destination")
        shutil.rmtree(temp_dir)
        sys.exit(1)

    # Verify we are NOT in the repo
    repo_root = Path(__file__).resolve().parent.parent
    try:
        portable_dir.relative_to(repo_root)
        fail("Portable directory is INSIDE the repo — isolation failed")
        shutil.rmtree(temp_dir)
        sys.exit(1)
    except ValueError:
        ok("Portable directory is OUTSIDE the repo — isolation confirmed")

    # Start portable Orion
    log("\nStarting portable Orion.exe...")
    env = os.environ.copy()
    env["ORION_DESKTOP"] = "1"
    env["ORION_PORTABLE_TEST"] = "1"

    proc = subprocess.Popen(
        [str(portable_exe), "--browser", "--no-tray"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        cwd=str(portable_dir),
    )

    port = 8000
    health_url = f"http://127.0.0.1:{port}/api/health"

    log("Waiting for backend (up to 30s)...")
    healthy = wait_for_health(health_url, timeout=30.0)
    if healthy:
        ok("Portable backend started and healthy")
    else:
        fail("Portable backend failed to start")
        proc.kill()
        shutil.rmtree(temp_dir)
        sys.exit(1)

    # Verify frontend
    status, body = http_get(f"http://127.0.0.1:{port}/")
    if status == 200:
        ok("Portable frontend serves")
    else:
        fail(f"Portable frontend returned HTTP {status}")

    # Verify full health
    status, body = http_get(health_url)
    if status == 200:
        ok("Portable health endpoint OK")
    else:
        fail(f"Portable health endpoint HTTP {status}")

    # Clean shutdown
    log("\nShutting down portable Orion...")
    proc.terminate()
    try:
        proc.wait(timeout=10.0)
        ok(f"Portable clean shutdown (exit {proc.returncode})")
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        fail("Portable forced kill")

    # Cleanup
    if not args.keep_temp:
        import time
        for attempt in range(3):
            try:
                shutil.rmtree(temp_dir)
                ok("Temp directory cleaned")
                break
            except PermissionError:
                if attempt < 2:
                    time.sleep(1)
                    continue
                log("Temp cleanup deferred (Windows file handle — auto-cleaned on reboot)")
    else:
        log(f"Temp directory kept: {temp_dir}")

    print(f"\n{'=' * 60}")
    print(f"  PORTABLE TEST: {PASS} passed, {FAIL} failed")
    print(f"{'=' * 60}\n")

    if FAIL > 0:
        print("  PORTABLE TEST FAILED — NO RELEASE")
        sys.exit(1)
    print("  Portable test PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
