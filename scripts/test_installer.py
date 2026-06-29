#!/usr/bin/env python3
"""ORION Installer Integrity Test.

Verifies that the NSIS installer produces a working installation.

Usage:
    python scripts/test_installer.py                          # Uses dist/OrionInstaller.exe
    python scripts/test_installer.py --installer path/to/OrionInstaller.exe
    python scripts/test_installer.py --installed-dir "C:\\Program Files\\ORION"

Steps:
  1. Run installer silently (/S)
  2. Verify installed files exist
  3. Start Orion.exe from installed location
  4. Verify health endpoint
  5. Verify frontend
  6. Clean shutdown
  7. Uninstall
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
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
    parser = argparse.ArgumentParser(description="ORION Installer Integrity Test")
    parser.add_argument("--installer", type=Path, default=None, help="Path to OrionInstaller.exe")
    parser.add_argument("--installed-dir", default=None, help="Expected install directory")
    parser.add_argument("--no-uninstall", action="store_true", help="Skip uninstall step")
    args = parser.parse_args()

    if args.installer:
        installer = args.installer.resolve()
    else:
        installer = Path(__file__).resolve().parent.parent / "dist" / "OrionInstaller.exe"

    if not installer.exists():
        print(f"\n\u2717 OrionInstaller.exe not found at: {installer}")
        print("  Build first: makensis installer\\orion.nsi")
        sys.exit(1)

    installed_dir = Path(args.installed_dir or r"C:\Program Files\ORION")

    print(f"\n{'=' * 60}")
    print("  ORION INSTALLER INTEGRITY TEST")
    print(f"  Installer: {installer}")
    print(f"  Target:    {installed_dir}")
    print(f"{'=' * 60}\n")

    if not sys.platform == "win32":
        log("Not on Windows — skipping NSIS installation test")
        log("Run this test on Windows after building OrionInstaller.exe")
        print(f"\n{'=' * 60}")
        print("  TEST SKIPPED (not Windows)")
        print(f"{'=' * 60}\n")
        sys.exit(0)

    # ── Step 1: Run installer silently (admin elevation required) ──
    log("Running installer silently (may prompt for admin elevation)...")
    try:
        import ctypes
        if ctypes.windll.shell32.IsUserAnAdmin():
            result = subprocess.run(
                [str(installer), "/S"],
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                fail(f"Installer returned exit code {result.returncode}")
                log(f"  stderr: {result.stderr[-300:]}")
                sys.exit(1)
        else:
            log("Not running as admin — attempting ShellExecute RunAs...")
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", str(installer), "/S", None, 0)
            if ret <= 32:
                fail(f"ShellExecute RunAs failed (err={ret}) — try running test as Administrator")
                sys.exit(1)
            log("Installer launched via RunAs, waiting for completion...")
            import time
            max_wait = 120
            while max_wait > 0 and not (installed_dir / "uninstall.exe").exists():
                time.sleep(1)
                max_wait -= 1
            if not (installed_dir / "uninstall.exe").exists():
                fail("Installer did not complete after 120s (uninstall.exe not found)")
                sys.exit(1)
        ok("Installer completed successfully")
    except ImportError:
        log("ctypes not available — falling back to subprocess")
        result = subprocess.run(
            [str(installer), "/S"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            ok("Installer completed successfully")
        else:
            fail(f"Installer returned exit code {result.returncode}")
            log(f"  stderr: {result.stderr[-300:]}")
            sys.exit(1)
    except subprocess.TimeoutExpired:
        fail("Installer timed out after 120s")
        sys.exit(1)
    except FileNotFoundError:
        fail("Installer not found or not executable")
        sys.exit(1)

    # ── Step 2: Verify installed files ───────────────────────────────
    log("\nVerifying installed files...")
    required = [
        installed_dir / "Orion.exe",
        installed_dir / "uninstall.exe",
        installed_dir / "LICENSE",
        installed_dir / "_internal" / "frontend_dist" / "index.html",
    ]
    all_files_ok = True
    for f in required:
        if f.exists():
            ok(f"  {f.relative_to(installed_dir.parent)} exists")
        else:
            fail(f"  {f.relative_to(installed_dir.parent)} MISSING")
            all_files_ok = False

    if not all_files_ok:
        fail("Installer did not copy all required files — installation incomplete")
        log("  See log above for missing files")
        if not args.no_uninstall:
            import ctypes
            ctypes.windll.shell32.ShellExecuteW(None, "runas", str(installed_dir / "uninstall.exe"), "/S", None, 0)
        sys.exit(1)

    ok("All required files installed")

    # ── Step 3: Start Orion from installed location ─────────────────
    log("\nStarting installed Orion.exe...")
    env = os.environ.copy()
    env["ORION_DESKTOP"] = "1"
    env["ORION_INSTALLER_TEST"] = "1"

    orion_exe = installed_dir / "Orion.exe"
    proc = subprocess.Popen(
        [str(orion_exe), "--browser", "--no-tray"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
        cwd=str(installed_dir),
    )

    port = 8000
    health_url = f"http://127.0.0.1:{port}/api/health"

    log("Waiting for backend (up to 30s)...")
    healthy = wait_for_health(health_url, timeout=30.0)
    if healthy:
        ok("Installed Orion backend started and healthy")
    else:
        fail("Installed Orion backend failed to start")
        log("  Checking logs...")
        logs_dir = Path(os.environ.get("APPDATA", "")) / "ORION" / "logs"
        if logs_dir.exists():
            for lf in logs_dir.iterdir():
                log(f"    {lf.name}: {lf.stat().st_size} bytes")
        proc.kill()
        if not args.no_uninstall:
            import ctypes
            ctypes.windll.shell32.ShellExecuteW(None, "runas", str(installed_dir / "uninstall.exe"), "/S", None, 0)
        sys.exit(1)

    # ── Step 4: Verify health endpoint ───────────────────────────────
    status, body = http_get(health_url)
    if status == 200:
        ok(f"Installed health endpoint OK (HTTP {status})")
    else:
        fail(f"Installed health endpoint HTTP {status}")

    # ── Step 5: Verify frontend ─────────────────────────────────────
    status, body = http_get(f"http://127.0.0.1:{port}/")
    if status == 200 and ("<html" in body.lower() or "<!doctype" in body.lower()):
        ok("Installed frontend serves correctly")
    elif status == 200:
        ok(f"Installed frontend root responds (HTTP {status})")
    else:
        fail(f"Installed frontend returned HTTP {status}")

    # ── Step 6: Clean shutdown ──────────────────────────────────────
    log("\nShutting down installed Orion...")
    proc.terminate()
    try:
        proc.wait(timeout=10.0)
        ok(f"Clean shutdown (exit {proc.returncode})")
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        fail("Forced kill — did not shut down cleanly")

    # ── Step 7: Uninstall (admin elevation required) ────────────────
    if not args.no_uninstall:
        log("\nRunning uninstaller...")
        try:
            uninstall_exe = installed_dir / "uninstall.exe"
            if uninstall_exe.exists():
                import ctypes
                if ctypes.windll.shell32.IsUserAnAdmin():
                    result = subprocess.run(
                        [str(uninstall_exe), "/S"],
                        capture_output=True, text=True, timeout=30,
                    )
                    if result.returncode == 0:
                        ok("Uninstaller completed successfully")
                    else:
                        fail(f"Uninstaller returned exit code {result.returncode}")
                else:
                    log("Not admin — attempting ShellExecute RunAs for uninstall...")
                    ctypes.windll.shell32.ShellExecuteW(None, "runas", str(uninstall_exe), "/S", None, 0)
                    import time
                    time.sleep(5)
                    if not uninstall_exe.exists():
                        ok("Uninstaller completed successfully (target removed)")
                    else:
                        fail("Uninstaller may have failed (target still exists)")
            else:
                fail("Uninstaller not found")
        except subprocess.TimeoutExpired:
            fail("Uninstaller timed out")
    else:
        skip("Uninstall skipped (--no-uninstall)")

    print(f"\n{'=' * 60}")
    print(f"  INSTALLER TEST: {PASS} passed, {FAIL} failed")
    print(f"{'=' * 60}\n")

    if FAIL > 0:
        print("  INSTALLATION FAILED — see errors above")
        print("  Installation may be partially functional")
        sys.exit(1)
    print("  Installer test PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
