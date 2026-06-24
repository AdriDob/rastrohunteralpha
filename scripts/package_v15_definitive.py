#!/usr/bin/env python3
"""Assemble Rastro v1.5 Definitive unified ZIP for all platforms.

Usage:
    python scripts/package_v15_definitive.py [--dest DIR] [--skip-windows]

Steps:
    1. Copy Linux binary from dist/Rastro/
    2. Copy Windows binary (see WINDOWS_SRC constant)
    3. Copy Android APK from dist/
    4. Copy docs, installer scripts, VERSION
    5. Create ZIP + SHA256
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
VERSION = (ROOT / "VERSION").read_text().strip()

WINDOWS_ZIP = ROOT / "dist" / "Rastro-1.4.0-rc2-final-unified.zip"

LINUX_SRC = DIST / "Rastro"
ANDROID_SRC = DIST / "rastro-android-debug.apk"

DOCS_SRC = [
    ROOT / "README.md",
    ROOT / "ARCHITECTURE.md",
    ROOT / "CHANGELOG.md",
    ROOT / "MANUAL_ES.md",
    ROOT / "RELEASE_NOTES.md",
    ROOT / "VALIDATION_REPORT.md",
    ROOT / "WINDOWS_RELEASE_AUDIT.md",
    ROOT / "FINAL_PACKAGE_AUDIT.md",
    ROOT / "DESKTOP_E2E_VALIDATION.md",
    ROOT / "INSTALL.md",
    ROOT / "ROOT_CAUSE_REPORT.md",
]
WINDOWS_INSTALLER = ROOT / "scripts" / "build_windows.ps1"
LINUX_INSTALLER = ROOT / "scripts" / "install_linux.sh"
VERSION_FILE = ROOT / "VERSION"


def _check_prerequisites(skip_windows: bool) -> None:
    missing: list[str] = []
    if not LINUX_SRC.exists():
        missing.append(f"Linux binary not found at {LINUX_SRC}")
    if not ANDROID_SRC.exists():
        missing.append(f"Android APK not found at {ANDROID_SRC}")
    if not skip_windows:
        if not WINDOWS_ZIP.exists():
            missing.append(f"Windows source ZIP not found at {WINDOWS_ZIP}")
        else:
            with zipfile.ZipFile(WINDOWS_ZIP) as zf:
                win_files = [n for n in zf.namelist() if n.startswith("Windows/")]
                if not win_files:
                    missing.append("No Windows/ entries in source ZIP")
    if missing:
        print("Missing prerequisites:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)
    print("  ✓ All prerequisites met")


def _make_zip_staging(dest_dir: Path, skip_windows: bool) -> Path:
    """Stage files in a temp directory, then create the ZIP."""
    staging = dest_dir / f"rastro-{VERSION}-staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    # ── VERSION ─────────────────────────────────────────────────
    shutil.copy2(VERSION_FILE, staging / "VERSION")
    print("  ✓ VERSION")

    # ── Linux binary ────────────────────────────────────────────
    linux_dir = staging / "Linux"
    shutil.copytree(LINUX_SRC, linux_dir, dirs_exist_ok=True)
    # Remove runtime artifacts (database, logs) from the package
    for pattern in ["database", "logs", "__pycache__"]:
        for p in linux_dir.rglob(pattern):
            if p.is_dir():
                shutil.rmtree(p)
    print(f"  ✓ Linux/ ({sum(f.stat().st_size for f in linux_dir.rglob('*')) / 1024 / 1024:.0f} MB)")

    # ── Windows binary (extract from RC2 ZIP) ───────────────────
    if not skip_windows:
        win_dir = staging / "Windows"
        with zipfile.ZipFile(WINDOWS_ZIP) as zf:
            for name in zf.namelist():
                if name.startswith("Windows/"):
                    target = staging / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not name.endswith("/"):
                        zf.extract(name, staging)
        win_size = sum(f.stat().st_size for f in win_dir.rglob("*")) / 1024 / 1024
        print(f"  ✓ Windows/ ({win_size:.0f} MB)")

    # ── Android APK ────────────────────────────────────────────
    android_dir = staging / "Android"
    android_dir.mkdir(exist_ok=True)
    shutil.copy2(ANDROID_SRC, android_dir / ANDROID_SRC.name)
    print(f"  ✓ Android/")

    # ── Docs ───────────────────────────────────────────────────
    docs_dir = staging / "docs"
    docs_dir.mkdir(exist_ok=True)
    for doc in DOCS_SRC:
        if doc.exists():
            shutil.copy2(doc, docs_dir / doc.name)
    print(f"  ✓ docs/")

    # ── Installer scripts ─────────────────────────────────────
    scripts_dir = staging / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    if WINDOWS_INSTALLER.exists():
        shutil.copy2(WINDOWS_INSTALLER, scripts_dir / WINDOWS_INSTALLER.name)
    if LINUX_INSTALLER.exists():
        shutil.copy2(LINUX_INSTALLER, scripts_dir / LINUX_INSTALLER.name)
    print(f"  ✓ scripts/")

    return staging


def _create_zip(staging: Path, dest_dir: Path) -> Path:
    zip_path = dest_dir / f"Rastro-{VERSION}-unified.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(staging):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(staging)
                zf.write(file_path, arcname)
    print(f"  ✓ ZIP: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.0f} MB)")
    return zip_path


def _generate_sha256(zip_path: Path, dest_dir: Path) -> Path:
    sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    sha_file = dest_dir / f"Rastro-{VERSION}-unified.zip.sha256"
    sha_file.write_text(f"{sha}  {zip_path.name}\n")
    print(f"  ✓ SHA256: {sha}")
    return sha_file


def _cleanup(staging: Path) -> None:
    shutil.rmtree(staging)
    print("  ✓ Staging cleaned")


def main() -> None:
    parser = argparse.ArgumentParser(description="Package Rastro v1.5 Definitive")
    parser.add_argument("--dest", default=str(ROOT / "dist"),
                        help="Output directory (default: dist/)")
    parser.add_argument("--skip-windows", action="store_true",
                        help="Skip Windows binary (for Linux-only builds)")
    parser.add_argument("--dest-windows", default="/mnt/c/Users/adrie/OneDrive/Desktop/PRUEBAS",
                        help="Windows destination for ZIP (default: PRUEBAS)")
    args = parser.parse_args()

    dest_dir = Path(args.dest)
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"Packaging Rastro v{VERSION} Definitive")
    print(f"  Destination: {dest_dir}")

    _check_prerequisites(args.skip_windows)

    print("\nStep 1: Staging files...")
    staging = _make_zip_staging(dest_dir, args.skip_windows)

    print("\nStep 2: Creating ZIP...")
    zip_path = _create_zip(staging, dest_dir)

    print("\nStep 3: Generating SHA256...")
    _generate_sha256(zip_path, dest_dir)

    print("\nStep 4: Cleaning up...")
    _cleanup(staging)

    # ── Copy to Windows PRUEBAS destination ────────────────────
    win_dest = Path(args.dest_windows)
    if win_dest.exists():
        win_zip = win_dest / zip_path.name
        try:
            shutil.copy2(zip_path, win_zip)
            print(f"  ✓ Also copied to: {win_zip}")
        except Exception as e:
            print(f"  ! Could not copy to Windows dest: {e}")

    print(f"\n{'='*50}")
    print(f"  Rastro v{VERSION} Definitive")
    print(f"  ZIP:  {zip_path}")
    print(f"  Size: {zip_path.stat().st_size / 1024 / 1024:.0f} MB")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
