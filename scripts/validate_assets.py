#!/usr/bin/env python3
"""ORION Asset Validation — verifies all required files exist in the release.

Usage:
    python scripts/validate_assets.py                              # Checks dist/Orion/
    python scripts/validate_assets.py --build-dir path/to/Orion    # Custom build
    python scripts/validate_assets.py --release                    # Checks build/release/
    python scripts/validate_assets.py --ci                         # CI mode (json output)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PASS = 0
FAIL = 0
WARN = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  \u2713 {label}")
    else:
        FAIL += 1
        print(f"  \u2717 {label} {detail}")


def warn(label: str, detail: str = "") -> None:
    global WARN
    WARN += 1
    print(f"  \u26a0 {label} {detail}")


def read_version(build_dir: Path) -> str:
    for candidate in [build_dir / "VERSION.txt", build_dir.parent / "VERSION"]:
        if candidate.exists():
            return candidate.read_text().strip()
    return "unknown"


def check_build(build_dir: Path, release_mode: bool = False) -> bool:
    global PASS, FAIL, WARN
    PASS = FAIL = WARN = 0

    print(f"\n{'=' * 60}")
    print("  ORION ASSET VALIDATION")
    print(f"  Directory: {build_dir}")
    print(f"{'=' * 60}\n")

    if release_mode:
        # Release mode: check build/release/ structure
        check("Directory exists", build_dir.is_dir())

        installer = build_dir / "OrionInstaller.exe"
        check("OrionInstaller.exe exists", installer.is_file())

        zip_file = list(build_dir.glob("Orion-*.zip"))
        check("Orion-*.zip exists", len(zip_file) > 0)

        docs = ["README.txt", "CHANGELOG.md", "VERSION.txt", "LICENSE.txt", "build_info.json"]
        for doc in docs:
            check(f"{doc} exists", (build_dir / doc).is_file())

        orion_dir = build_dir / "Orion"
        check("Orion/ subdirectory exists", orion_dir.is_dir())

        if orion_dir.is_dir():
            check_orion_bundle(orion_dir)
    else:
        # Build mode: check dist/Orion/
        check("Directory exists", build_dir.is_dir())
        check_orion_bundle(build_dir)

    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {PASS} OK, {FAIL} FAIL, {WARN} WARN")
    print(f"{'=' * 60}\n")

    return FAIL == 0


def check_orion_bundle(orion_dir: Path) -> None:
    is_win = sys.platform.startswith("win")
    exe_name = "Orion.exe" if is_win else "Orion"

    # Core executable
    exe = orion_dir / exe_name
    check(f"{exe_name} exists", exe.is_file())
    if exe.is_file():
        check(f"{exe_name} > 1 MB", exe.stat().st_size > 1_000_000,
              f"({exe.stat().st_size / 1024 / 1024:.1f} MB)")

    internal = orion_dir / "_internal"

    # Frontend assets (try _internal/ first, then bundle root)
    frontend = (internal / "frontend_dist") if internal.is_dir() and (internal / "frontend_dist").is_dir() else orion_dir / "frontend_dist"
    check("frontend_dist/ exists", frontend.is_dir())
    if frontend.is_dir():
        check("frontend_dist/index.html exists",
              (frontend / "index.html").is_file())
        check("frontend_dist/assets/ exists",
              (frontend / "assets").is_dir())
        asset_count = len(list(frontend.rglob("*")))
        check(f"frontend_dist/ has files ({asset_count})",
              asset_count > 5)

    # Internal PyInstaller files
    check("_internal/ exists (PyInstaller runtime)", internal.is_dir())
    if internal.is_dir():
        # Python source files — compiled into PYZ on PyInstaller 6.x (all platforms)
        py_count = len(list(internal.rglob("*.py")))
        if py_count > 0:
            check(f"_internal/ has Python files ({py_count})", True)
        else:
            warn("_internal/ Python files compiled into PYZ (PyInstaller 6.x norm)")

        # Native modules
        native_pattern = "*.pyd" if is_win else "*.so"
        native_count = len(list(internal.rglob(native_pattern)))
        if is_win:
            native_count += len(list(internal.rglob("*.dll")))
        # Also check for .pyd inside base_library.zip (not applicable, but check the pattern)
        check(f"_internal/ has native modules ({native_count})",
              native_count > 0)

    # Critical Python modules — compiled into PYZ, not individual files.
    # Verify by checking that base_library.zip or PYZ archive exists.
    if internal.is_dir():
        pyz_found = (internal / "base_library.zip").exists() or \
                    len(list(internal.rglob("PYZ-*.pyz"))) > 0
        if not pyz_found:
            # Fallback: check for any zip files
            zips = list(internal.rglob("*.zip"))
            pyz_found = len(zips) > 0
        check("Python bytecode archive exists (PYZ)", pyz_found)

    # VERSION file (try _internal/ first, then bundle root)
    version_file = (internal / "VERSION") if internal.is_dir() and (internal / "VERSION").is_file() else orion_dir / "VERSION"
    check("VERSION file exists", version_file.is_file())
    if version_file.is_file():
        version = version_file.read_text().strip()
        check(f"VERSION is valid ({version})",
              len(version) > 0 and version[0].isdigit())

    # Icon (if available)
    icon = orion_dir / "orion.ico"
    if icon.exists():
        check("orion.ico exists", True)
    else:
        warn("orion.ico not found in bundle (may be embedded in exe)")

    # Size sanity
    total_bytes = sum(f.stat().st_size for f in orion_dir.rglob("*") if f.is_file())
    total_mb = total_bytes / 1024 / 1024
    check(f"Total bundle size ({total_mb:.1f} MB)", total_mb > 5,
          detail="(expected > 5 MB for a complete build)")
    check(f"Bundle not oversized ({total_mb:.1f} MB)", total_mb < 2000,
          detail="(expected < 2 GB)")


def main() -> None:
    parser = argparse.ArgumentParser(description="ORION Asset Validation")
    parser.add_argument("--build-dir", type=Path, default=None, help="Path to Orion build directory")
    parser.add_argument("--release", action="store_true", help="Check release output (build/release/)")
    parser.add_argument("--ci", action="store_true", help="CI mode")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent

    if args.build_dir:
        build_dir = args.build_dir.resolve()
    elif args.release:
        build_dir = project_root / "build" / "release"
    else:
        build_dir = project_root / "dist" / "Orion"

    success = check_build(build_dir, release_mode=args.release)

    if args.json:
        result = {
            "success": success,
            "pass": PASS,
            "fail": FAIL,
            "warn": WARN,
            "directory": str(build_dir),
        }
        print(json.dumps(result, indent=2))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
