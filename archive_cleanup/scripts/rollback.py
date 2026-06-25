#!/usr/bin/env python3
"""Rollback helper — restores previous release artifact.

Usage:
    python scripts/rollback.py [--version X.Y.Z]

Looks in dist/artifacts/ for the target version manifest
and restores the previous build's web assets.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
FRONTEND = ROOT / "frontend"


def list_versions() -> list[str]:
    artifacts_dir = DIST / "artifacts"
    if not artifacts_dir.exists():
        return []
    return sorted([
        f.name.replace("rastro-", "").replace("-manifest.json", "")
        for f in artifacts_dir.glob("rastro-*-manifest.json")
    ])


def rollback_to(version: str) -> None:
    manifest_path = DIST / "artifacts" / f"rastro-{version}-manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: No manifest found for v{version}")
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text())
    print(f"Rolling back to Rastro v{version} ({manifest['date']})")

    web_backup = DIST / "pwa" / "web"
    if web_backup.exists():
        target = FRONTEND / "dist"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(web_backup, target)
        print(f"  ✓ Restored web assets from {web_backup}")
    else:
        print("  WARNING: No web backup found")

    print(f"  ✓ Rollback to v{version} complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rollback Rastro release")
    parser.add_argument("--version", help="Target version (default: previous)")
    args = parser.parse_args()

    versions = list_versions()
    if not versions:
        print("No release artifacts found in dist/artifacts/")
        sys.exit(0)

    target = args.version or (versions[-2] if len(versions) >= 2 else versions[-1])
    rollback_to(target)


if __name__ == "__main__":
    main()
