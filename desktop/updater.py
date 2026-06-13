"""Auto-Update Framework — checks GitHub Releases for new versions.

Design:
  - Non-blocking on startup (runs in background thread)
  - Uses GitHub Releases API to check for updates
  - Downloads ZIP asset, verifies checksum, applies by swapping binaries
  - Safe rollback on crash after update
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request

logger = logging.getLogger("rastro.desktop.updater")

GITHUB_REPO = "AdriDob/rastrohunteralpha"
UPDATE_STAGING_DIR = Path(__file__).resolve().parent / "build" / ".updates"
ROLLBACK_DIR = Path(__file__).resolve().parent / "build" / ".rollback"
ROLLBACK_FLAG = Path.home() / ".rastro" / ".update_pending"

# Timeout in seconds after which a boot after update is considered successful
BOOT_GRACE_SECONDS = 15


@dataclass
class ReleaseInfo:
    version: str
    download_url: str
    checksum_sha256: str
    release_notes_url: str = ""
    required: bool = False


def _get_exe_dir() -> Path:
    """Get the directory containing the current executable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent / "dist" / "Rastro"


def _parse_semver(v: str) -> tuple[int, int, int]:
    parts = v.lstrip("vV").split(".")
    return tuple(int(p) for p in parts[:3])  # type: ignore[return-value]


def _current_version() -> str:
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.0.0"


def check_for_updates(current_version: str | None = None) -> Optional[ReleaseInfo]:
    """Check GitHub Releases for a newer version.

    Returns ReleaseInfo if an update is available, None otherwise.
    """
    version = current_version or _current_version()
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    try:
        req = Request(api_url, headers={"User-Agent": "Rastro/1.0", "Accept": "application/json"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.warning("Failed to check for updates: %s", exc)
        return None

    latest_tag = data.get("tag_name", "")
    if not latest_tag:
        return None

    try:
        latest_ver = _parse_semver(latest_tag)
        current_ver = _parse_semver(version)
    except (ValueError, TypeError):
        return None

    if latest_ver <= current_ver:
        logger.debug("Already up to date (%s)", version)
        return None

    # Find the ZIP asset for the current platform
    platform_suffix = "Windows" if sys.platform == "win32" else "Linux"
    assets = data.get("assets", [])
    target_asset = None
    checksum_asset = None

    for asset in assets:
        name = asset.get("name", "")
        if platform_suffix in name and name.endswith(".zip"):
            target_asset = asset
        if "checksums" in name or "sha256" in name:
            checksum_asset = asset

    if not target_asset:
        logger.warning("No %s ZIP asset found in release %s", platform_suffix, latest_tag)
        return None

    download_url = target_asset["browser_download_url"]
    checksum_sha256 = ""

    if checksum_asset:
        try:
            with urlopen(checksum_asset["browser_download_url"], timeout=10) as resp:
                checksum_text = resp.read().decode("utf-8")
                for line in checksum_text.strip().split("\n"):
                    if target_asset["name"] in line:
                        checksum_sha256 = line.split()[0].strip().lower()
                        break
        except Exception:
            pass

    release_notes_url = data.get("html_url", "")

    return ReleaseInfo(
        version=latest_tag.lstrip("vV"),
        download_url=download_url,
        checksum_sha256=checksum_sha256,
        release_notes_url=release_notes_url,
    )


def download_update(release: ReleaseInfo) -> Optional[str]:
    """Download the update ZIP to staging directory.

    Returns the path to the downloaded ZIP, or None on failure.
    """
    UPDATE_STAGING_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPDATE_STAGING_DIR / f"rastro-{release.version}.zip"

    if dest.exists():
        logger.debug("Update already downloaded: %s", dest)
        return str(dest)

    logger.info("Downloading update %s from %s", release.version, release.download_url)
    try:
        req = Request(release.download_url, headers={"User-Agent": "Rastro/1.0"})
        with urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = int(downloaded / total * 100)
                        if pct % 25 == 0:
                            logger.debug("Downloaded %d%% of %d bytes", pct, total)
        logger.info("Download complete: %s (%d bytes)", dest, downloaded)
        return str(dest)
    except Exception as exc:
        logger.error("Download failed: %s", exc)
        if dest.exists():
            dest.unlink()
        return None


def verify_checksum(filepath: str, expected_sha256: str) -> bool:
    """Verify the downloaded file's SHA-256 checksum."""
    if not expected_sha256:
        logger.warning("No checksum provided for verification — skipping")
        return True

    logger.debug("Verifying checksum for %s", filepath)
    try:
        with open(filepath, "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()
        match = actual.lower() == expected_sha256.lower()
        if match:
            logger.info("Checksum verified: %s", filepath)
        else:
            logger.error("Checksum mismatch: expected %s, got %s", expected_sha256, actual)
        return match
    except Exception as exc:
        logger.error("Checksum verification failed: %s", exc)
        return False


def _extract_zip(zip_path: str, dest_dir: Path) -> bool:
    """Extract a ZIP file to the destination directory."""
    import zipfile
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest_dir)
        logger.info("Extracted %s to %s", zip_path, dest_dir)
        return True
    except Exception as exc:
        logger.error("Extraction failed: %s", exc)
        return False


def apply_update(release: ReleaseInfo, downloaded_path: str) -> bool:
    """Apply the downloaded update.

    1. Backup current binary
    2. Extract new version
    3. Set rollback flag
    4. Restart the app
    """
    exe_dir = _get_exe_dir()
    if not exe_dir.exists():
        logger.error("Current installation not found at %s", exe_dir)
        return False

    # 1. Backup current installation
    ROLLBACK_DIR.mkdir(parents=True, exist_ok=True)
    backup_dir = ROLLBACK_DIR / f"backup-{_current_version()}"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    try:
        shutil.copytree(exe_dir, backup_dir)
        logger.info("Backed up current version to %s", backup_dir)
    except Exception as exc:
        logger.error("Backup failed: %s", exc)
        return False

    # 2. Create a temp dir and extract there, then swap
    extract_dir = UPDATE_STAGING_DIR / f"extracted-{release.version}"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)

    if not _extract_zip(downloaded_path, extract_dir):
        return False

    # Find the binary inside the extracted ZIP
    extracted_exe = None
    for candidate in ["Rastro.exe", "Rastro", "run.exe", "run"]:
        p = extract_dir / candidate
        if p.exists():
            extracted_exe = p
            break
    # Try nested directories
    if not extracted_exe:
        for item in extract_dir.iterdir():
            if item.is_dir():
                for candidate in ["Rastro.exe", "Rastro", "run.exe", "run"]:
                    p = item / candidate
                    if p.exists():
                        extracted_exe = p
                        break
            if extracted_exe:
                break

    if not extracted_exe:
        logger.error("No executable found in extracted archive")
        return False

    try:
        # Remove current and copy new
        shutil.rmtree(exe_dir)
        shutil.copytree(extracted_exe.parent if extracted_exe.parent != extract_dir else extract_dir, exe_dir)
    except Exception as exc:
        logger.error("Failed to swap binaries: %s", exc)
        return False

    # 3. Set rollback flag
    ROLLBACK_FLAG.parent.mkdir(parents=True, exist_ok=True)
    ROLLBACK_FLAG.write_text(json.dumps({
        "previous_version": _current_version(),
        "new_version": release.version,
        "applied_at": time.time(),
        "backup_path": str(backup_dir),
    }))

    # 4. Update VERSION file
    version_file = Path(__file__).resolve().parent.parent / "VERSION"
    version_file.write_text(release.version + "\n")

    logger.info("Update to %s applied. Restart to activate.", release.version)
    return True


def mark_update_success() -> None:
    """Clear the rollback flag after a successful boot."""
    if ROLLBACK_FLAG.exists():
        ROLLBACK_FLAG.unlink()
        logger.info("Update boot verified — rollback flag cleared")


def rollback() -> bool:
    """Rollback to the previous version after a failed update."""
    if not ROLLBACK_FLAG.exists():
        return False

    try:
        data = json.loads(ROLLBACK_FLAG.read_text())
    except (json.JSONDecodeError, OSError):
        ROLLBACK_FLAG.unlink()
        return False

    backup_path = Path(data.get("backup_path", ""))
    exe_dir = _get_exe_dir()

    if not backup_path.exists():
        logger.error("Rollback backup not found at %s", backup_path)
        ROLLBACK_FLAG.unlink()
        return False

    try:
        if exe_dir.exists():
            shutil.rmtree(exe_dir)
        shutil.copytree(backup_path, exe_dir)
        logger.info("Rolled back to version %s", data.get("previous_version", "unknown"))

        # Restore VERSION
        version_file = Path(__file__).resolve().parent.parent / "VERSION"
        version_file.write_text(data.get("previous_version", "0.0.0") + "\n")
    except Exception as exc:
        logger.error("Rollback failed: %s", exc)
        return False
    finally:
        ROLLBACK_FLAG.unlink()

    return True


def check_and_rollback_if_needed() -> bool:
    """Check if a rollback is needed (crash after update).

    Should be called early in the boot sequence.
    Returns True if rollback was performed.
    """
    if ROLLBACK_FLAG.exists():
        logger.warning("Previous update detected without successful boot — rolling back")
        return rollback()
    return False
