#!/usr/bin/env python3
"""Rastro release automation.

Usage:
    python scripts/release.py <version>   # e.g. "0.4.0"
    python scripts/release.py --dry-run   # preview without committing

Steps:
    1. Read current VERSION
    2. Validate semver
    3. Update VERSION file
    4. Stage, commit, tag
    5. Push (unless --dry-run)
"""

import re
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT / "VERSION"
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def read_version() -> str:
    return VERSION_FILE.read_text().strip()


def write_version(v: str) -> None:
    VERSION_FILE.write_text(v + "\n")


def validate_semver(v: str) -> None:
    if not SEMVER_RE.match(v):
        print(f"error: '{v}' is not a valid semver (X.Y.Z)")
        sys.exit(1)


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=PROJECT, check=check)


def main() -> None:
    dry = "--dry-run" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args:
        current = read_version()
        print(f"Current version: {current}")
        print(f"Usage: {sys.argv[0]} <version>")
        sys.exit(0)

    new_ver = args[0]
    validate_semver(new_ver)

    current = read_version()
    print(f"Releasing: {current} → {new_ver}")

    write_version(new_ver)
    print(f"  VERSION: {new_ver}")

    if dry:
        print("  [dry-run] skipping commit, tag, push")
        return

    run(["git", "add", "VERSION"])
    run(["git", "commit", "-m", f"chore: bump version to {new_ver}"])
    run(["git", "tag", f"v{new_ver}"])
    run(["git", "push", "origin", "main", "--tags"])

    print(f"Released v{new_ver}")
    print(f"  → https://github.com/tu-usuario/rastro/releases/tag/v{new_ver}")


if __name__ == "__main__":
    main()
