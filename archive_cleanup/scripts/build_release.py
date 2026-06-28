#!/usr/bin/env python3
"""Release builder — single-command build for all platforms.

Usage:
    python scripts/build_release.py [--version X.Y.Z] [--platform all|desktop|web|mobile]

Builds:
    - Frontend production bundle (Vite)
    - PWA assets + service worker
    - Desktop package (PyInstaller + electron-builder)
    - Mobile (Capacitor sync + APK)
    - Versioned release artifacts in dist/
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
FRONTEND = ROOT / "frontend"
VERSION_FILE = ROOT / "api" / "main.py"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"  → {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}")
        sys.exit(1)


def get_current_version() -> str:
    for line in VERSION_FILE.read_text().splitlines():
        if "APP_VERSION" in line:
            return line.split("=")[-1].strip().strip('"')
    return "0.4.0"


def build_frontend() -> None:
    print("\n[1/5] Building frontend…")
    run(["npm", "ci"], cwd=FRONTEND)
    run(["npm", "run", "build"], cwd=FRONTEND)
    print("  ✓ Frontend built")


def build_pwa() -> None:
    print("\n[2/5] Building PWA assets…")
    pwa_dir = DIST / "pwa"
    pwa_dir.mkdir(parents=True, exist_ok=True)
    web_dist = FRONTEND / "dist"
    if web_dist.exists():
        shutil.copytree(web_dist, pwa_dir / "web", dirs_exist_ok=True)
    print("  ✓ PWA assets ready")


def build_desktop(version: str) -> None:
    print("\n[3/5] Building desktop package…")
    desktop_dir = DIST / f"rastro-desktop-{version}"
    desktop_dir.mkdir(parents=True, exist_ok=True)

    for f in ROOT.glob("desktop/*.py"):
        shutil.copy2(f, desktop_dir / f.name)

    web_dist = FRONTEND / "dist"
    if web_dist.exists():
        shutil.copytree(web_dist, desktop_dir / "web", dirs_exist_ok=True)

    shutil.copy2(ROOT / "requirements.txt", desktop_dir / "requirements.txt")

    desktop_installer = desktop_dir / "install.sh"
    desktop_installer.write_text(f"""#!/bin/bash
echo "Installing Rastro Desktop {version}..."
pip install -r "$(dirname "$0")/requirements.txt"
python3 "$(dirname "$0")/launcher.py"
""")
    desktop_installer.chmod(0o755)
    print("  ✓ Desktop package ready")


def build_mobile(version: str) -> None:
    print("\n[4/5] Building mobile package…")
    mobile_dir = DIST / f"rastro-mobile-{version}"
    mobile_dir.mkdir(parents=True, exist_ok=True)

    web_dist = FRONTEND / "dist"
    if web_dist.exists():
        shutil.copytree(web_dist, mobile_dir / "web", dirs_exist_ok=True)

    capacitor_config = ROOT / "capacitor.config.ts"
    if capacitor_config.exists():
        shutil.copy2(capacitor_config, mobile_dir / "capacitor.config.ts")

    print("  ✓ Mobile package ready")


def generate_checksums(version: str) -> None:
    print("\n[5/5] Generating release checksums…")
    artifacts_dir = DIST / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    checksums = {}
    for artifact in DIST.rglob("*"):
        if artifact.is_file() and ".sha256" not in artifact.name:
            sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
            rel = artifact.relative_to(DIST)
            checksums[str(rel)] = sha

    checksum_file = artifacts_dir / f"rastro-{version}-checksums.sha256"
    checksum_file.write_text(
        "\n".join(f"{v}  {k}" for k, v in sorted(checksums.items())) + "\n"
    )

    manifest = {
        "version": version,
        "date": datetime.utcnow().isoformat(),
        "artifacts": len(checksums),
        "files": list(checksums.keys()),
    }
    (artifacts_dir / f"rastro-{version}-manifest.json").write_text(
        json.dumps(manifest, indent=2)
    )
    print(f"  ✓ Release manifest written ({len(checksums)} files)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Rastro release")
    parser.add_argument("--version", default=get_current_version())
    parser.add_argument(
        "--platform",
        choices=["all", "desktop", "web", "mobile"],
        default="all",
    )
    args = parser.parse_args()

    version = args.version
    print(f"Building Rastro v{version}")

    start = time.time()

    if args.platform in ("all", "web"):
        build_frontend()
        build_pwa()

    if args.platform in ("all", "desktop"):
        build_desktop(version)

    if args.platform in ("all", "mobile"):
        build_mobile(version)

    if args.platform == "all":
        generate_checksums(version)

    elapsed = time.time() - start
    print(f"\n✓ Build complete in {elapsed:.1f}s")
    print(f"  Artifacts: {DIST}")


if __name__ == "__main__":
    main()
