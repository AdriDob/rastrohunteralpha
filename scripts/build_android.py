#!/usr/bin/env python3
"""Android APK Builder — single-command Capacitor sync + APK generation.

Usage:
    python scripts/build_android.py                     # Debug APK
    python scripts/build_android.py --release           # Release APK (requires keystore)
    python scripts/build_android.py --clean             # Clean + rebuild

Prerequisites:
    - Node.js, npm
    - Android SDK (ANDROID_HOME set)
    - Java 17+
    - Gradle (or use the android/gradlew wrapper)

Build steps:
    1. Install frontend deps + build (npm ci && npm run build)
    2. Capacitor sync (npx cap sync android)
    3. Gradle assemble (debug or release)
    4. Copy APK to dist/
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
ANDROID = ROOT / "android"
OUTPUT = ROOT / "dist" / "android"


def _banner(msg: str) -> None:
    print(f"\n=== {msg} ===")


def _run(cmd: list[str], cwd: Path | None = None, **kwargs) -> subprocess.CompletedProcess:
    print(f"  → {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd or ROOT, **kwargs)
    if result.returncode != 0:
        print(f"  ERROR: command failed (exit {result.returncode})")
        sys.exit(1)
    return result


def _check_prerequisites() -> None:
    missing: list[str] = []
    try:
        subprocess.run(["node", "--version"], capture_output=True, text=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        missing.append("Node.js")

    try:
        subprocess.run(["npm", "--version"], capture_output=True, text=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        missing.append("npm")

    android_home = os.environ.get("ANDROID_HOME")
    if not android_home:
        android_home = os.environ.get("ANDROID_SDK_ROOT")
    if not android_home or not Path(android_home).is_dir():
        missing.append("ANDROID_HOME / Android SDK")

    try:
        subprocess.run(["java", "--version"], capture_output=True, text=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        missing.append("Java 17+")

    if missing:
        print("  Missing prerequisites:")
        for m in missing:
            print(f"    - {m}")
        sys.exit(1)

    print("  ✓ All prerequisites met")


def _build_frontend() -> None:
    _banner("Building frontend")
    _run(["npm", "ci"], cwd=FRONTEND)
    _run(["npm", "run", "build"], cwd=FRONTEND)
    print("  ✓ Frontend built")


def _cap_sync() -> None:
    _banner("Syncing Capacitor")
    _run(["npx", "cap", "sync", "android"])
    print("  ✓ Capacitor synced")


def _build_apk(release: bool, clean: bool) -> Path:
    _banner("Building APK")
    if not ANDROID.is_dir():
        print(f"  ERROR: android/ directory not found at {ANDROID}")
        print("  Run 'npx cap add android' first to generate the Android project")
        sys.exit(1)

    gradlew = ANDROID / "gradlew"
    gradle_exe = ANDROID / "gradle"
    if gradlew.exists():
        gradle_cmd = [str(gradlew)]
    elif gradle_exe.exists():
        gradle_cmd = [str(gradle_exe)]
    else:
        gradle_cmd = ["gradle"]

    if clean:
        _run(gradle_cmd + ["clean"], cwd=ANDROID)

    task = "assembleRelease" if release else "assembleDebug"
    _run(gradle_cmd + [task], cwd=ANDROID)

    flavor = "release" if release else "debug"
    apk_path = ANDROID / "app" / "build" / "outputs" / "apk" / flavor / f"app-{flavor}.apk"
    if not apk_path.exists():
        print(f"  ERROR: APK not found at expected path: {apk_path}")
        print("  Check android/app/build/outputs/apk/")
        sys.exit(1)

    apk_size = apk_path.stat().st_size / 1024 / 1024
    print(f"  ✓ APK ready: {apk_path} ({apk_size:.1f} MB)")
    return apk_path


def _copy_artifact(apk: Path, release: bool) -> Path:
    _banner("Copying APK to dist/")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    flavor = "release" if release else "debug"
    dest = OUTPUT / f"Rastro-{flavor}.apk"
    shutil.copy2(apk, dest)
    print(f"  ✓ APK copied: {dest} ({dest.stat().st_size / 1024 / 1024:.1f} MB)")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Rastro Android APK")
    parser.add_argument("--release", action="store_true", help="Build release APK (requires keystore)")
    parser.add_argument("--clean", action="store_true", help="Clean build artifacts before building")
    parser.add_argument("--skip-prereqs", action="store_true", help="Skip prerequisite checks")
    args = parser.parse_args()

    print("Building Rastro Android APK")
    if args.release:
        print("  Mode: release")
    else:
        print("  Mode: debug")

    if not args.skip_prereqs:
        _check_prerequisites()
    _build_frontend()
    _cap_sync()
    apk = _build_apk(release=args.release, clean=args.clean)
    dest = _copy_artifact(apk, release=args.release)

    print("\n=== Build complete ===")
    print(f"  APK: {dest}")
    if args.release:
        print("  Ready for distribution")
    else:
        print(f"  Install on device: adb install {dest}")


if __name__ == "__main__":
    main()
