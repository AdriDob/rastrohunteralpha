#!/usr/bin/env python3
"""ORION — Final output assembly script.

Assembles all build artifacts into the target output directory:
    C:/Users/adrie/OneDrive/Desktop/Yo/privado/Orion

Structure:
    Orion/
      Orion.exe
      frontend_dist/
      _internal/
    OrionInstaller.exe
    Orion-<version>.zip
    README.txt
    VERSION.txt
    build_info.json

Usage:
    python scripts/assemble_output.py                    # Default output
    python scripts/assemble_output.py --output PATH      # Custom output
    python scripts/assemble_output.py --version X.Y.Z    # Custom version
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DIST_DIR = PROJECT_ROOT / "dist"
VERSION_FILE = PROJECT_ROOT / "VERSION"

_OUTPUT_ENV = os.environ.get("ORION_OUTPUT_DIR")


def _default_output() -> Path:
    if _OUTPUT_ENV:
        return Path(_OUTPUT_ENV)
    if sys.platform == "win32":
        return Path(os.environ.get("USERPROFILE", "C:/")) / "OneDrive" / "Desktop" / "Yo" / "privado"
    return PROJECT_ROOT / "dist" / "orion-release"


def log(step: str, msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{step:>20}] {msg}")


def read_version() -> str:
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return "1.6.0"


# ── Step 1: Find artifacts ─────────────────────────────────────────────


def find_pyinstaller_bundle() -> Path | None:
    candidates = [
        DIST_DIR / "Orion",
        PROJECT_ROOT / "desktop" / "build" / "dist" / "Orion",
    ]
    for c in candidates:
        if c.is_dir() and (c / "Orion.exe").exists():
            log("PYINSTALLER", f"Found: {c}")
            return c
    log("PYINSTALLER", "No PyInstaller bundle found. Run pyinstaller Orion.spec -y first.")
    return None


def find_frontend_dist() -> Path | None:
    dist = FRONTEND_DIR / "dist"
    if dist.is_dir() and (dist / "index.html").is_file():
        log("FRONTEND", f"Found: {dist}")
        return dist
    log("FRONTEND", "Not found. Run: cd frontend && npm ci && npm run build")
    return None


def find_installer() -> Path | None:
    installer = DIST_DIR / "OrionInstaller.exe"
    if installer.exists():
        log("INSTALLER", f"Found: {installer} ({installer.stat().st_size / 1024 / 1024:.1f} MB)")
        return installer
    log("INSTALLER", "Not found. Run: makensis /DPRODUCT_VERSION=X.Y.Z installer\\orion.nsi")
    return None


# ── Step 2: Assemble output ────────────────────────────────────────────


def assemble_output(
    output_dir: Path,
    version: str,
    pyinstaller_bundle: Path | None,
    frontend_dist: Path | None,
    installer: Path | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    log("OUTPUT", f"Target: {output_dir}")

    app_dir = output_dir / "Orion"
    app_dir.mkdir(exist_ok=True)

    if pyinstaller_bundle:
        dest = app_dir
        for item in pyinstaller_bundle.iterdir():
            if item.is_dir():
                shutil.copytree(item, dest / item.name, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest / item.name)
        size_mb = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file()) / 1024 / 1024
        log("OUTPUT", f"  Orion/ — {size_mb:.1f} MB")
    else:
        log("OUTPUT", "  Orion/ — skipped (no PyInstaller bundle)")

    if frontend_dist:
        dest = app_dir / "frontend_dist"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(frontend_dist, dest)
        size_kb = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file()) / 1024
        log("OUTPUT", f"  Orion/frontend_dist/ — {size_kb:.0f} KB")

    if installer:
        shutil.copy2(installer, output_dir / installer.name)
        log("OUTPUT", f"  {installer.name} — copied")

    _write_readme(output_dir, version)
    _write_version(output_dir, version)
    _write_build_info(output_dir, version, pyinstaller_bundle is not None)

    _create_zip(output_dir, version)

    log("OUTPUT", "Assembly complete")
    _print_summary(output_dir)


def _write_readme(output_dir: Path, version: str) -> None:
    readme = output_dir / "README.txt"
    readme.write_text(
        f"\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557\n"
        f"\u2551         ORION v{version.ljust(6)}               \u2551\n"
        f"\u2551   Automated Security Investigation OS    \u2551\n"
        f"\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d\n"
        f"\n"
        f"  Dashboard:  http://127.0.0.1:8000\n"
        f"  Website:    https://orion.security\n"
        f"\n"
        f"---  Getting Started  ---\n"
        f"\n"
        f"  1. Run Orion\\Orion.exe --tray\n"
        f"     (starts in system tray, no terminal)\n"
        f"\n"
        f"  2. Open http://127.0.0.1:8000 in your browser\n"
        f"     (or double-click the desktop shortcut)\n"
        f"\n"
        f"  3. The ORION icon appears in the system tray\n"
        f"     Right-click for: Open Dashboard, Stop, View Logs\n"
        f"\n"
        f"---  System Requirements  ---\n"
        f"\n"
        f"  * Windows 11 64-bit\n"
        f"  * 4 GB RAM (8 GB recommended)\n"
        f"  * No Python or Node.js required\n"
        f"\n"
        f"---  v{version} - {datetime.now().strftime('%Y-%m-%d')}  ---\n"
    )
    log("DOCS", f"  README.txt ({readme.stat().st_size} bytes)")


def _write_version(output_dir: Path, version: str) -> None:
    version_txt = output_dir / "VERSION.txt"
    version_txt.write_text(f"{version}\n")
    log("DOCS", f"  VERSION.txt ({version_txt.stat().st_size} bytes)")


def _write_build_info(output_dir: Path, version: str, has_bundle: bool) -> None:
    info = {
        "app": "ORION",
        "version": version,
        "build_date": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "has_pyinstaller_bundle": has_bundle,
        "files": {},
    }
    for f in output_dir.rglob("*"):
        if f.is_file():
            rel = str(f.relative_to(output_dir))
            info["files"][rel] = {
                "size_bytes": f.stat().st_size,
                "size_human": (
                    f"{f.stat().st_size / 1024:.1f} KB"
                    if f.stat().st_size < 1024 * 1024
                    else f"{f.stat().st_size / 1024 / 1024:.1f} MB"
                ),
            }
    build_info = output_dir / "build_info.json"
    build_info.write_text(json.dumps(info, indent=2))
    log("DOCS", f"  build_info.json ({build_info.stat().st_size} bytes)")


def _create_zip(output_dir: Path, version: str) -> Path | None:
    zip_path = output_dir / f"Orion-{version}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for root, _dirs, files in os.walk(output_dir):
            for file in files:
                if file.endswith(".zip"):
                    continue
                full_path = Path(root) / file
                arcname = str(full_path.relative_to(output_dir))
                zf.write(full_path, arcname)

    if zip_path.exists():
        log("ZIP", f"  Orion-{version}.zip ({zip_path.stat().st_size / 1024 / 1024:.1f} MB)")
        return zip_path
    log("ZIP", "Failed to create ZIP")
    return None


def _print_summary(output_dir: Path) -> None:
    total_mb = sum(f.stat().st_size for f in output_dir.rglob("*") if f.is_file()) / 1024 / 1024
    print()
    print("  " + "\u2500" * 20)
    print(f"  Output:    {output_dir}")
    print(f"  Total:     {total_mb:.1f} MB")
    print()
    print(f"  To run:    {output_dir / 'Orion' / 'Orion.exe'} --tray")
    print(f"  Installer:     {output_dir / 'OrionInstaller.exe'}")
    print("  Dashboard:     http://127.0.0.1:8000")
    print("  " + "\u2500" * 20)


# ── Main ─────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="ORION — assemble final output artifacts")
    parser.add_argument("--output", type=Path, default=None, help="Output directory")
    parser.add_argument("--version", default=None, help="Version override")
    parser.add_argument("--validate", action="store_true", help="Run asset validation after assembly")
    args = parser.parse_args()

    version = args.version or read_version()
    output_dir = args.output or _default_output()

    log("ASSEMBLE", f"ORION v{version} — output assembly")
    log("ASSEMBLE", f"Platform: {sys.platform}")

    pyinstaller_bundle = find_pyinstaller_bundle()
    frontend_dist = find_frontend_dist()
    installer = find_installer()

    if not pyinstaller_bundle and not frontend_dist:
        log("ASSEMBLE", "WARNING: No build artifacts found.")
        log("ASSEMBLE", "  PyInstaller: pyinstaller Orion.spec -y")
        log("ASSEMBLE", "  NSIS:        makensis installer\\orion.nsi")

    assemble_output(output_dir, version, pyinstaller_bundle, frontend_dist, installer)

    if args.validate:
        log("ASSEMBLE", "Running asset validation...")
        from scripts.validate_assets import check_build
        success = check_build(output_dir, release_mode=True)
        if success:
            log("ASSEMBLE", "Asset validation PASSED")
        else:
            log("ASSEMBLE", "Asset validation FAILED")
            sys.exit(1)


if __name__ == "__main__":
    main()
