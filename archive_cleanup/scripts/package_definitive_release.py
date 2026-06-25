#!/usr/bin/env python3
"""Rastro v1.5.0 Definitive Release Packaging.

Packages:
  - Linux desktop binary (dist/Rastro/)
  - Android APK (dist/rastro-android-debug.apk)
  - Documentation files
  - Configuration files
  - Installer scripts

Usage:
    python scripts/package_definitive_release.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
VERSION = (ROOT / "VERSION").read_text().strip()

LINUX_SRC = DIST / "Rastro"
ANDROID_SRC = DIST / "rastro-android-debug.apk"
PORTABLE_ZIP = DIST / f"Rastro-Portable-{VERSION}.zip"

DOCS = [
    ROOT / "README.md",
    ROOT / "ARCHITECTURE.md",
    ROOT / "CHANGELOG.md",
    ROOT / "RELEASE_NOTES.md",
    ROOT / "INSTALL.md",
    ROOT / "MANUAL_ES.md",
    ROOT / "GUIA_RAPIDA.md",
    ROOT / "VALIDATION_REPORT.md",
    ROOT / "FINAL_PACKAGE_AUDIT.md",
    ROOT / "FINAL_STABILITY_REPORT.md",
    ROOT / "DESKTOP_E2E_VALIDATION.md",
    ROOT / "ROOT_CAUSE_REPORT.md",
    ROOT / "REAL_WORLD_VALIDATION.md",
]

SCRIPTS = [
    ROOT / "scripts" / "build.sh",
    ROOT / "scripts" / "build_linux.sh",
    ROOT / "scripts" / "build_frontend.sh",
    ROOT / "scripts" / "build_android.py",
    ROOT / "scripts" / "build_release.py",
    ROOT / "scripts" / "install_windows.py",
    ROOT / "scripts" / "package_portable.py",
]

CONFIG_FILES = [
    ROOT / "capacitor.config.json",
    ROOT / "Rastro.spec",
    ROOT / "requirements.txt",
    ROOT / "VERSION",
]

ASSETS = [
    ROOT / "installer" / "icons" / "rastro.ico",
    ROOT / "installer" / "icons" / "rastro.png",
]


def fmt_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check_prerequisites() -> None:
    missing = []
    if not LINUX_SRC.exists():
        missing.append(f"Linux binary not found at {LINUX_SRC}")
    if not (LINUX_SRC / "Rastro").exists():
        missing.append(f"Linux executable not found at {LINUX_SRC / 'Rastro'}")
    if not ANDROID_SRC.exists():
        missing.append(f"Android APK not found at {ANDROID_SRC}")
    if not PORTABLE_ZIP.exists():
        print(f"  ! Portable ZIP not found (non-fatal): {PORTABLE_ZIP}")
    if missing:
        print("Missing prerequisites:")
        for m in missing:
            print(f"  - {m}")
        sys.exit(1)
    print("  All prerequisites met")


def assemble_package(dest: Path, include_portable: bool = True) -> Path:
    """Assemble all release artifacts into a staging directory."""
    staging = dest / f"rastro-{VERSION}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    files_added = []

    def add(src: Path, dst_rel: str) -> None:
        dst = staging / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
        files_added.append(dst_rel)

    add(VERSION_FILE := ROOT / "VERSION", "VERSION")
    add(LINUX_SRC, "Linux")
    add(ANDROID_SRC, f"Android/{ANDROID_SRC.name}")
    if include_portable and PORTABLE_ZIP.exists():
        add(PORTABLE_ZIP, f"ZIP/{PORTABLE_ZIP.name}")

    for doc in DOCS:
        if doc.exists():
            add(doc, f"docs/{doc.name}")

    for script in SCRIPTS:
        if script.exists():
            add(script, f"scripts/{script.name}")

    for cfg in CONFIG_FILES:
        if cfg.exists():
            add(cfg, f"config/{cfg.name}")

    for asset in ASSETS:
        if asset.exists():
            add(asset, f"assets/{asset.name}")

    print(f"  Staged {len(files_added)} files ({fmt_size(sum(f.stat().st_size for f in staging.rglob('*') if f.is_file()))})")
    return staging


def create_release_zip(staging: Path, dest: Path) -> Path:
    zip_path = dest / f"Rastro-{VERSION}-definitive.zip"
    if zip_path.exists():
        zip_path.unlink()

    total = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for root, _dirs, files in os.walk(staging):
            for file in files:
                file_path = Path(root) / file
                arcname = str(file_path.relative_to(staging))
                zf.write(file_path, arcname)
                total += 1

    size = zip_path.stat().st_size
    print(f"  ZIP: {zip_path}")
    print(f"  Entries: {total}")
    print(f"  Size: {fmt_size(size)}")
    return zip_path


def generate_checksums(dest: Path, zip_path: Path) -> dict:
    checksums = {}

    for f in sorted(dest.iterdir()):
        if f.is_file() and f.suffix not in (".sha256", ".json"):
            checksums[f.name] = sha256_file(f)

    sha_file = dest / f"Rastro-{VERSION}-checksums.sha256"
    sha_file.write_text(
        "\n".join(f"{v}  {k}" for k, v in sorted(checksums.items())) + "\n"
    )
    print(f"  Checksums: {sha_file} ({len(checksums)} files)")

    manifest = {
        "version": VERSION,
        "date": datetime.now(timezone.utc).isoformat(),
        "artifacts": len(checksums),
        "files": list(checksums.keys()),
        "checksums": checksums,
    }
    manifest_file = dest / f"Rastro-{VERSION}-manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2))
    print(f"  Manifest: {manifest_file}")

    return checksums


def copy_to_target(src: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.is_file():
            dst = target / item.name
            shutil.copy2(item, dst)

    items = list(target.iterdir())
    print(f"  Copied {len(items)} files to {target}")
    for i in items:
        print(f"    {i.name} ({fmt_size(i.stat().st_size)})")


def verify_zip(zip_path: Path) -> dict:
    result = {"path": str(zip_path), "valid": False, "entries": 0, "total_size": 0, "missing": []}

    if not zip_path.exists():
        result["missing"].append("ZIP file does not exist")
        return result

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            bad = zf.testzip()
            if bad:
                result["missing"].append(f"Corrupted entry: {bad}")
                return result

            names = zf.namelist()
            result["entries"] = len(names)
            result["total_size"] = zip_path.stat().st_size

            expected = {
                "Linux/_internal/": "Desktop runtime",
                "Linux/Rastro": "Desktop binary",
            }
            for prefix, desc in expected.items():
                found = any(n.startswith(prefix) for n in names)
                if not found:
                    result["missing"].append(f"Missing: {desc} ({prefix}*)")

            android_found = any(n.startswith("Android/") and n.endswith(".apk") for n in names)
            if not android_found:
                result["missing"].append("Missing: Android APK")

            docs_count = sum(1 for n in names if n.startswith("docs/"))
            if docs_count == 0:
                result["missing"].append("Missing: Documentation")

        result["valid"] = len(result["missing"]) == 0
    except Exception as e:
        result["missing"].append(f"ZIP error: {e}")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Package Rastro Definitive Release")
    parser.add_argument("--dest", default=str(DIST), help="Output directory")
    parser.add_argument("--no-portable", action="store_true", help="Skip portable ZIP")
    parser.add_argument("--target", default="/mnt/c/Users/adrie/OneDrive/Desktop/Yo/privado",
                        help="Final target directory")
    args = parser.parse_args()

    dest_dir = Path(args.dest)
    target_dir = Path(args.target)
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"Rastro v{VERSION} Definitive Release Packaging")
    print(f"  Source: {dest_dir}")
    print(f"  Target: {target_dir}")
    print()

    print("[1/6] Checking prerequisites...")
    check_prerequisites()

    print("\n[2/6] Assembling package...")
    staging = assemble_package(dest_dir, include_portable=not args.no_portable)

    print("\n[3/6] Creating release ZIP...")
    zip_path = create_release_zip(staging, dest_dir)

    print("\n[4/6] Generating checksums and manifest...")
    generate_checksums(dest_dir, zip_path)

    print("\n[5/6] Verifying ZIP integrity...")
    verification = verify_zip(zip_path)
    if verification["valid"]:
        print(f"  ZIP valid: {verification['entries']} entries, {fmt_size(verification['total_size'])}")
    else:
        print(f"  ZIP issues found:")
        for m in verification["missing"]:
            print(f"    - {m}")

    print("\n[6/6] Copying to target directory...")
    copy_to_target(dest_dir, target_dir)

    print(f"\n{'='*55}")
    print(f"  Rastro v{VERSION} Definitive Release")
    print(f"  Release ZIP: {zip_path.name}")
    print(f"  Size: {fmt_size(zip_path.stat().st_size)}")
    print(f"  SHA256: {sha256_file(zip_path)}")
    print(f"  Target: {target_dir}")
    print(f"{'='*55}")

    shutil.rmtree(staging)
    print("\n  Staging cleaned. Release complete.")


if __name__ == "__main__":
    main()
