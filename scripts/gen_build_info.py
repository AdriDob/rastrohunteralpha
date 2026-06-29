#!/usr/bin/env python3
"""Generate build_info.json for the build/release/ directory."""
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

RELEASE_DIR = Path("build/release")
VERSION = "1.6.0"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_git_commit():
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def main():
    total = sum(f.stat().st_size for f in RELEASE_DIR.rglob("*") if f.is_file())

    hashes = {}
    for f in RELEASE_DIR.rglob("*"):
        if f.is_file() and f.name in ("Orion.exe", "Orion", "OrionInstaller.exe"):
            hashes[f.name] = sha256(f)

    files = {}
    for f in sorted(RELEASE_DIR.rglob("*")):
        if f.is_file():
            relp = str(f.relative_to(RELEASE_DIR))
            sz = f.stat().st_size
            human = f"{sz/1024:.1f} KB" if sz < 1024 * 1024 else f"{sz/1024/1024:.1f} MB"
            files[relp] = {"size_bytes": sz, "size_human": human}

    info = {
        "app": "ORION",
        "version": VERSION,
        "build_id": f"ORION-v{VERSION}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "build_date": datetime.now(timezone.utc).isoformat(),
        "commit": get_git_commit(),
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "total_size_bytes": total,
        "total_size_human": f"{total/1024/1024:.1f} MB",
        "components": {
            "frontend": True,
            "pyinstaller": True,
            "installer": True,
            "docs": True,
        },
        "sha256": hashes,
        "files": files,
    }

    (RELEASE_DIR / "build_info.json").write_text(json.dumps(info, indent=2))
    print(f"build_info.json generated — {len(files)} files indexed")


if __name__ == "__main__":
    main()
