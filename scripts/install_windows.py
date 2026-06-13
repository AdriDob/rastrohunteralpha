#!/usr/bin/env python3
"""Windows Installer — single-command desktop build + packaging.

Usage:
    python scripts/install_windows.py                    # Portable folder + zip
    python scripts/install_windows.py --installer        # Also try NSIS installer
    python scripts/install_windows.py --version 1.0.0    # Custom version

Build steps:
    1. Install frontend deps + build (npm ci && npm run build)
    2. Bundle Python backend via PyInstaller (--onedir for Windows)
    3. Assemble portable folder with frontend dist, binary, scripts
    4. Optionally create NSIS installer (if makensis is on PATH)
    5. Output artifacts to dist/install-windows/
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
BUILD_SCRIPT = ROOT / "desktop" / "build" / "build_desktop.py"
OUTPUT = ROOT / "dist" / "install-windows"

VERSION_FILE = ROOT / "api" / "main.py"


def _banner(msg: str) -> None:
    print(f"\n=== {msg} ===")


def _run(cmd: list[str], cwd: Path | None = None, **kwargs) -> subprocess.CompletedProcess:
    print(f"  → {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, cwd=cwd or ROOT, **kwargs)
    if result.returncode != 0:
        print(f"  ERROR: command failed (exit {result.returncode})")
        sys.exit(1)
    return result


def _get_version() -> str:
    for line in VERSION_FILE.read_text().splitlines():
        if "APP_VERSION" in line:
            return line.split("=")[-1].strip().strip('"')
    return "0.4.0"


def _ensure_frontend_built() -> None:
    dist_dir = FRONTEND / "dist"
    if dist_dir.is_dir() and (dist_dir / "index.html").exists():
        print("  Frontend dist exists — skipping build (delete frontend/dist to force)")
        return
    _banner("Building frontend")
    _run(["npm", "ci"], cwd=FRONTEND)
    _run(["npm", "run", "build"], cwd=FRONTEND)
    print("  ✓ Frontend built")


def _run_pyinstaller() -> Path:
    _banner("Running PyInstaller bundler")
    _run([sys.executable, str(BUILD_SCRIPT), "--onedir", "--rebuild-frontend"])
    build_dist = ROOT / "desktop" / "build" / "dist"
    exe = build_dist / "Rastro" / "Rastro.exe"
    if not exe.exists():
        print(f"  ERROR: expected executable not found at {exe}")
        print("  Check desktop/build/dist/ for the build output")
        sys.exit(1)
    print(f"  ✓ PyInstaller bundle ready: {exe}")
    return build_dist


def _assemble_portable(version: str, build_dist: Path) -> Path:
    _banner("Assembling portable folder")
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    bundle = OUTPUT / f"Rastro-{version}-win64"
    bundle.mkdir(parents=True, exist_ok=True)

    pyinstaller_out = build_dist / "Rastro"
    for item in pyinstaller_out.iterdir():
        dest = bundle / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    frontend_dist = FRONTEND / "dist"
    if frontend_dist.is_dir():
        shutil.copytree(frontend_dist, bundle / "frontend_dist", dirs_exist_ok=True)

    readme = bundle / "README.txt"
    readme.write_text(
        f"""Rastro v{version} — Windows Portable Edition
{'=' * 50}

Run:  Rastro.exe

First launch will:
  - Initialize the database in %APPDATA%\\Rastro\\database\\
  - Create logs in %APPDATA%\\Rastro\\logs\\
  - Open the web interface in your default browser

System Requirements:
  - Windows 10 or later (64-bit)
  - No Python or Node.js required

To uninstall, delete this folder and %APPDATA%\\Rastro\\
"""
    )

    print(f"  ✓ Portable folder: {bundle}")
    return bundle


def _create_zip(bundle: Path) -> Path:
    _banner("Creating release zip")
    zip_path = bundle.parent / f"{bundle.name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in bundle.rglob("*"):
            arcname = str(file.relative_to(bundle.parent))
            zf.write(file, arcname)
    print(f"  ✓ Zip created: {zip_path} ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")
    return zip_path


def _try_nsis_installer(version: str, bundle: Path) -> Path | None:
    if not shutil.which("makensis"):
        print("  makensis not found — skipping NSIS installer (install NSIS to enable)")
        return None

    _banner("Creating NSIS installer")
    nsis_script = OUTPUT / "installer.nsi"
    nsis_script.write_text(
        f"""!define PRODUCT_NAME "Rastro"
!define PRODUCT_VERSION "{version}"
!define PRODUCT_PUBLISHER "Rastro AI"
!define PRODUCT_WEB_SITE "https://rastro.ai"

Name "${{PRODUCT_NAME}} ${{PRODUCT_VERSION}}"
OutFile "Rastro-{version}-setup-win64.exe"
InstallDir "$PROGRAMFILES64\\${{PRODUCT_NAME}}"
RequestExecutionLevel admin

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "{bundle}\\*.*"
  CreateShortCut "$DESKTOP\\Rastro.lnk" "$INSTDIR\\Rastro.exe"
  CreateDirectory "$SMPROGRAMS\\Rastro"
  CreateShortCut "$SMPROGRAMS\\Rastro\\Rastro.lnk" "$INSTDIR\\Rastro.exe"
  CreateShortCut "$SMPROGRAMS\\Rastro\\Uninstall.lnk" "$INSTDIR\\uninstall.exe"
  WriteUninstaller "$INSTDIR\\uninstall.exe"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{PRODUCT_NAME}}" \\
                   "DisplayName" "${{PRODUCT_NAME}}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{PRODUCT_NAME}}" \\
                   "UninstallString" "$\"$INSTDIR\\uninstall.exe$\""
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{PRODUCT_NAME}}" \\
                   "DisplayVersion" "${{PRODUCT_VERSION}}"
  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{PRODUCT_NAME}}" \\
                   "Publisher" "${{PRODUCT_PUBLISHER}}"
SectionEnd

Section "Uninstall"
  RMDir /r "$INSTDIR"
  Delete "$DESKTOP\\Rastro.lnk"
  RMDir /r "$SMPROGRAMS\\Rastro"
  DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{PRODUCT_NAME}}"
SectionEnd
"""
    )
    _run(["makensis", str(nsis_script)], cwd=OUTPUT)
    installer = OUTPUT / f"Rastro-{version}-setup-win64.exe"
    if installer.exists():
        print(f"  ✓ NSIS installer: {installer} ({installer.stat().st_size / 1024 / 1024:.1f} MB)")
        return installer
    print("  NSIS installer failed — portable folder available instead")
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Windows installer for Rastro")
    parser.add_argument("--version", default=_get_version(), help="Release version string")
    parser.add_argument("--installer", action="store_true", help="Attempt NSIS installer creation")
    args = parser.parse_args()

    version = args.version
    print(f"Building Rastro v{version} for Windows")
    print(f"Output: {OUTPUT}")

    _ensure_frontend_built()
    build_dist = _run_pyinstaller()
    bundle = _assemble_portable(version, build_dist)
    zip_path = _create_zip(bundle)

    installer_path = None
    if args.installer:
        installer_path = _try_nsis_installer(version, bundle)

    _banner("Build complete")
    print(f"  Portable folder:   {bundle}")
    print(f"  Release zip:       {zip_path}")
    if installer_path:
        print(f"  Installer:         {installer_path}")
    print(f"\nRun 'Rastro.exe' to start the desktop application.")
    print(f"Logs and data will be stored in %APPDATA%\\Rastro\\")


if __name__ == "__main__":
    main()
