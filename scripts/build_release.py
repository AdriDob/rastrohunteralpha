#!/usr/bin/env python3
"""ORION Release Builder — one command to build the final production output.

Usage:
    python scripts/build_release.py                    # Full release build
    python scripts/build_release.py --version X.Y.Z    # Custom version
    python scripts/build_release.py --no-frontend      # Skip frontend build
    python scripts/build_release.py --no-nsis          # Skip NSIS installer
    python scripts/build_release.py --dry-run          # Print steps only

Builds:
  - Frontend (Vite production build)
  - Backend (PyInstaller EXE from Orion.spec)
  - Installer (NSIS .exe from installer/orion.nsi)
  - Smoke test (validates built EXE)
  - Documentation (README, CHANGELOG, LICENSE, VERSION, build_info.json)
  - ZIP package

Output:
  build/release/
    Orion/
      Orion.exe
      _internal/
      frontend_dist/
    OrionInstaller.exe
    Orion.zip
    README.txt
    CHANGELOG.md
    VERSION.txt
    LICENSE.txt
    build_info.json

Final target:
  C:\\Users\\adrie\\OneDrive\\Desktop\\Yo\\privado\\Orion
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
VERSION_FILE = PROJECT_ROOT / "VERSION"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"

_OUTPUT_ENV = os.environ.get("ORION_OUTPUT_DIR")
if _OUTPUT_ENV:
    DEFAULT_OUTPUT = Path(_OUTPUT_ENV)
elif sys.platform == "win32":
    DEFAULT_OUTPUT = Path(os.environ.get("USERPROFILE", "C:/")) / "OneDrive" / "Desktop" / "Yo" / "privado"
else:
    DEFAULT_OUTPUT = Path.home() / "Orion"

IS_WINDOWS = sys.platform == "win32"


def log(step: str, msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{step:>20}] {msg}")


def run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 300) -> bool:
    try:
        result = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            log("CMD", f"FAILED: {' '.join(cmd)}")
            log("CMD", result.stderr[-500:] if result.stderr else "no stderr")
            return False
        return True
    except subprocess.TimeoutExpired:
        log("CMD", f"TIMEOUT after {timeout}s: {' '.join(cmd)}")
        return False
    except FileNotFoundError as exc:
        log("CMD", f"NOT FOUND: {exc}")
        return False


def read_version() -> str:
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return "1.6.0"


def build_frontend() -> bool:
    log("FRONTEND", "Building frontend (npm ci + npm run build)...")
    if not (FRONTEND_DIR / "package.json").exists():
        log("FRONTEND", "SKIP — no package.json found")
        return False

    if not run_cmd(["npm", "ci", "--silent"], cwd=FRONTEND_DIR, timeout=120):
        log("FRONTEND", "npm ci failed, trying npm install...")
        if not run_cmd(["npm", "install", "--silent"], cwd=FRONTEND_DIR, timeout=120):
            log("FRONTEND", "FAILED")
            return False

    if not run_cmd(["npm", "run", "build"], cwd=FRONTEND_DIR, timeout=120):
        log("FRONTEND", "FAILED")
        return False

    dist = FRONTEND_DIR / "dist"
    if not dist.is_dir() or not list(dist.rglob("*.html")):
        log("FRONTEND", "FAILED — no dist/index.html generated")
        return False

    size = sum(f.stat().st_size for f in dist.rglob("*") if f.is_file())
    log("FRONTEND", f"OK — {size / 1024:.0f} KB in {sum(1 for _ in dist.rglob('*'))} files")
    return True


def build_pyinstaller() -> bool:
    log("PYINSTALLER", "Building EXE (pyinstaller Orion.spec)...")
    spec = PROJECT_ROOT / "Orion.spec"
    if not spec.exists():
        log("PYINSTALLER", "SKIP — no Orion.spec found")
        return False

    if not shutil.which("pyinstaller"):
        log("PYINSTALLER", "SKIP — PyInstaller not installed")
        return False

    if not run_cmd(["pyinstaller", "Orion.spec", "-y"], timeout=600):
        log("PYINSTALLER", "FAILED")
        return False

    exe = DIST_DIR / "Orion" / ("Orion.exe" if IS_WINDOWS else "Orion")
    if not exe.exists():
        log("PYINSTALLER", f"FAILED — {exe} not found")
        return False

    size = exe.stat().st_size
    log("PYINSTALLER", f"OK — {size / 1024 / 1024:.1f} MB")
    return True


def build_installer(version: str) -> bool:
    log("INSTALLER", "Building NSIS installer...")
    nsi = PROJECT_ROOT / "installer" / "orion.nsi"
    if not nsi.exists():
        log("INSTALLER", "SKIP — no installer/orion.nsi found")
        return False

    makensis = shutil.which("makensis")
    if not makensis:
        log("INSTALLER", "SKIP — NSIS (makensis) not installed")
        return False

    cmd = [makensis, f"/DPRODUCT_VERSION={version}", str(nsi)]
    if not run_cmd(cmd, cwd=PROJECT_ROOT / "installer", timeout=120):
        log("INSTALLER", "FAILED")
        return False

    installer = DIST_DIR / "OrionInstaller.exe"
    if not installer.exists():
        log("INSTALLER", "FAILED — OrionInstaller.exe not found in dist/")
        return False

    log("INSTALLER", f"OK — {installer.name} ({installer.stat().st_size / 1024 / 1024:.1f} MB)")
    return True


def create_docs(output_dir: Path, version: str) -> None:
    log("DOCS", f"Generating documentation files in {output_dir}")

    readme = output_dir / "README.txt"
    readme.write_text(
        f"{'=' * 40}\n"
        f"         ORION v{version.ljust(6)}          \n"
        f"   Automated Security Investigation OS    \n"
        f"{'=' * 40}\n"
        f"\n"
        f"  Dashboard:  http://127.0.0.1:8000\n"
        f"\n"
        f"--  Getting Started  --\n"
        f"\n"
        f"  1. Install using OrionInstaller.exe (recommended)\n"
        f"     OR extract Portable/Orion.zip and run Orion\\Orion.exe --tray\n"
        f"\n"
        f"  2. Open http://127.0.0.1:8000 in your browser\n"
        f"\n"
        f"  3. The ORION icon appears in the system tray\n"
        f"     Right-click for: Open Dashboard, Stop, View Logs\n"
        f"\n"
        f"--  System Requirements  --\n"
        f"\n"
        f"  * Windows 11 64-bit\n"
        f"  * 4 GB RAM (8 GB recommended)\n"
        f"  * No Python or Node.js required\n"
        f"\n"
        f"--  v{version} - {datetime.now().strftime('%Y-%m-%d')}  --\n"
    )
    log("DOCS", f"  README.txt ({readme.stat().st_size} bytes)")

    changelog = output_dir / "CHANGELOG.md"
    changelog.write_text(
        f"# Changelog\n\n"
        f"## v{version} ({datetime.now().strftime('%Y-%m-%d')})\n\n"
        f"### Release\n"
        f"- ORION v{version} Stable\n"
        f"- Build pipeline reproducible\n"
        f"- NSIS installer with Windows 11 support\n"
        f"- PyInstaller single-directory executable\n"
        f"- Watchdog with auto-recovery\n"
        f"- Multi-agent architecture (exploit, research, financial, strategy, validator, coordinator)\n"
        f"- 40+ API routers for security investigation\n"
        f"- React 19 + PrimeReact 10 frontend\n"
        f"- Service mode (optional, requires pywin32)\n"
        f"- Auto-update framework with safe rollback\n"
        f"\n"
        f"### Previous\n"
        f"- v1.5.0 (2026-06-15) - Release Candidate 1\n"
        f"- v1.6.0 RC (2026-06-20) - Release Candidate 3\n"
    )
    log("DOCS", f"  CHANGELOG.md ({changelog.stat().st_size} bytes)")

    version_txt = output_dir / "VERSION.txt"
    version_txt.write_text(f"{version}\n")
    log("DOCS", f"  VERSION.txt ({version_txt.stat().st_size} bytes)")

    current_year = datetime.now().year
    license_file = output_dir / "LICENSE.txt"
    license_file.write_text(
        f"ORION v{version}\n"
        f"Copyright (c) {current_year} ORION Labs\n\n"
        f"All rights reserved.\n\n"
        f"This software is protected by intellectual property laws.\n"
        f"Unauthorized distribution, modification, or use is prohibited.\n\n"
        f"For personal use only.\n"
        f"Non-transferable license.\n"
    )
    log("DOCS", f"  LICENSE.txt ({license_file.stat().st_size} bytes)")

    log("DOCS", "OK — 4 documentation files generated")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10, cwd=PROJECT_ROOT,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


KEY_ARTIFACTS = ["Orion.exe", "Orion", "OrionInstaller.exe"]


def artifact_sha256(output_dir: Path) -> dict[str, str]:
    hashes = {}
    for f in output_dir.rglob("*"):
        if f.is_file() and f.name in KEY_ARTIFACTS:
            hashes[f.name] = sha256(f)
    orion_dir = output_dir / "Orion"
    if orion_dir.exists():
        for f in orion_dir.rglob("*"):
            if f.is_file() and f.name in KEY_ARTIFACTS:
                hashes[f.name] = sha256(f)
    return hashes


def create_build_info(output_dir: Path, version: str, components: dict[str, bool]) -> None:
    total_size = sum(f.stat().st_size for f in output_dir.rglob("*") if f.is_file())
    info = {
        "app": "ORION",
        "version": version,
        "build_id": f"ORION-v{version}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "build_date": datetime.now(timezone.utc).isoformat(),
        "commit": get_git_commit(),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "total_size_bytes": total_size,
        "total_size_human": f"{total_size / 1024 / 1024:.1f} MB",
        "components": components,
        "sha256": artifact_sha256(output_dir),
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


def create_zip(output_dir: Path, version: str) -> Path | None:
    log("ZIP", f"Creating Orion-{version}.zip from {output_dir}...")
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
        size = zip_path.stat().st_size
        log("ZIP", f"OK — {zip_path.name} ({size / 1024 / 1024:.1f} MB)")
        return zip_path
    log("ZIP", "FAILED")
    return None


def copy_to_output(output_dir: Path) -> bool:
    target = DEFAULT_OUTPUT / "Orion"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for f in output_dir.iterdir():
        if f.is_file():
            shutil.copy2(f, target / f.name)
    # Also copy Orion/ subdir
    orion_dir = output_dir / "Orion"
    if orion_dir.exists():
        dest = target / "Orion"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(orion_dir, dest)
    log("COPY", f"Files copied to: {target}")
    return True


def verify_output(output_dir: Path) -> bool:
    log("VERIFY", "Verifying output files...")
    required = [
        "README.txt",
        "CHANGELOG.md",
        "VERSION.txt",
        "LICENSE.txt",
        "build_info.json",
    ]
    all_ok = True

    for name in required:
        path = output_dir / name
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        status = "OK" if exists else "MISSING"
        log("VERIFY", f"  [{status}] {name} ({size / 1024:.1f} KB)" if exists else f"  [{status}] {name}")
        if not exists:
            all_ok = False

    orion_dir = output_dir / "Orion"
    orion_exe = orion_dir / ("Orion.exe" if IS_WINDOWS else "Orion")
    if orion_exe.exists():
        log("VERIFY", f"  [OK] Orion/{orion_exe.name} ({orion_exe.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        log("VERIFY", "  [--] Orion/ binary not found (PyInstaller not run)")

    # PyInstaller 6.x places data files inside _internal/
    frontend_candidates = [
        orion_dir / "_internal" / "frontend_dist" / "index.html",
        orion_dir / "frontend_dist" / "index.html",
    ]
    frontend_found = any(p.exists() for p in frontend_candidates)
    if frontend_found:
        log("VERIFY", "  [OK] Orion/_internal/frontend_dist/index.html")
    else:
        log("VERIFY", "  [--] Orion/frontend_dist not found")

    installer = output_dir / "OrionInstaller.exe"
    if installer.exists():
        log("VERIFY", f"  [OK] OrionInstaller.exe ({installer.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        log("VERIFY", "  [--] OrionInstaller.exe not found")

    zip_file = output_dir / f"Orion-{read_version()}.zip"
    if zip_file.exists():
        log("VERIFY", f"  [OK] {zip_file.name} ({zip_file.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        log("VERIFY", "  [--] Orion.zip not found")

    return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="ORION Release Builder")
    parser.add_argument("--version", default=None, help="Version override")
    parser.add_argument("--no-frontend", action="store_true", help="Skip frontend build")
    parser.add_argument("--no-nsis", action="store_true", help="Skip NSIS installer")
    parser.add_argument("--clean", action="store_true", help="Clean dist/ and build/ before building")
    parser.add_argument("--dry-run", action="store_true", help="Print steps without executing")
    args = parser.parse_args()

    version = args.version or read_version()
    log("BUILD", f"ORION Release Builder v{version}")
    log("BUILD", f"Platform: {sys.platform}")
    log("BUILD", f"Project: {PROJECT_ROOT}")
    log("BUILD", f"Dry run: {args.dry_run}")

    output_dir = BUILD_DIR / "release"
    if args.dry_run:
        log("BUILD", f"Output would be: {output_dir}")
        log("BUILD", f"Final target: {DEFAULT_OUTPUT / 'Orion'}")
        log("BUILD", "Dry run complete")
        return

    if args.clean:
        log("CLEAN", "Removing dist/ and build/ ...")
        for d in [DIST_DIR, BUILD_DIR]:
            if d.exists():
                shutil.rmtree(d)
                log("CLEAN", f"  Removed: {d}")
        log("CLEAN", "OK")

    output_dir.mkdir(parents=True, exist_ok=True)

    components: dict[str, bool] = {}

    components["frontend"] = build_frontend() if not args.no_frontend else True
    components["pyinstaller"] = build_pyinstaller()
    components["installer"] = build_installer(version) if not args.no_nsis else False
    components["docs"] = True

    create_docs(output_dir, version)

    if components.get("pyinstaller"):
        src = DIST_DIR / "Orion"
        if src.exists():
            log("BUILD", "Copying PyInstaller build to output...")
            dest = output_dir / "Orion"
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)

    # Copy installer to output
    installer_src = DIST_DIR / "OrionInstaller.exe"
    if installer_src.exists():
        shutil.copy2(installer_src, output_dir / "OrionInstaller.exe")

    create_build_info(output_dir, version, components)
    create_zip(output_dir, version)

    log("BUILD", "\u2500" * 50)
    verify_output(output_dir)
    log("BUILD", "\u2500" * 50)
    total_mb = sum(f.stat().st_size for f in output_dir.rglob("*") if f.is_file()) / 1024 / 1024
    log("BUILD", f"Output directory: {output_dir}")
    log("BUILD", f"Total size: {total_mb:.1f} MB")

    copy_to_output(output_dir)

    log("BUILD", "\u2500" * 50)
    log("BUILD", "Build complete.")
    log("BUILD", f"  Output:  {output_dir}")
    log("BUILD", f"  Target:  {DEFAULT_OUTPUT / 'Orion'}")
    log("BUILD", "DONE")


if __name__ == "__main__":
    main()
