"""Package Rastro Desktop as a portable ZIP archive.

Usage:
    python scripts/package_portable.py                    # Uses existing dist/Rastro/
    python scripts/package_portable.py --source path/to/Rastro  # Custom source
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import zipfile
from pathlib import Path


def create_portable_zip(source_dir: Path, output_dir: Path, version: str = "1.0.0") -> Path:
    """Create a portable ZIP of the Rastro Desktop build."""
    if not source_dir.is_dir():
        print(f"Error: Source directory not found: {source_dir}")
        print("Run 'pyinstaller Rastro.spec --clean -y' first.")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"Rastro-Portable-{version}.zip"

    if zip_path.exists():
        zip_path.unlink()

    print(f"Creating portable ZIP: {zip_path}")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for root, _dirs, files in os.walk(source_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = str(file_path.relative_to(source_dir.parent))
                zf.write(file_path, arcname)

    print(f"  Size: {format_size(zip_path.stat().st_size)}")
    return zip_path


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def main() -> None:
    parser = argparse.ArgumentParser(description="Package Rastro Desktop as portable ZIP")
    parser.add_argument("--source", type=Path, default=Path("dist/Rastro"),
                        help="Path to PyInstaller build output (default: dist/Rastro)")
    parser.add_argument("--output", type=Path, default=Path("dist"),
                        help="Output directory (default: dist)")
    parser.add_argument("--version", default="1.0.0", help="Version string")
    args = parser.parse_args()

    zip_path = create_portable_zip(args.source.resolve(), args.output.resolve(), args.version)
    sha256 = compute_sha256(zip_path)
    print(f"  SHA-256: {sha256}")

    # Write checksum file
    sha_path = args.output / "SHA256SUMS.txt"
    with open(sha_path, "a") as f:
        f.write(f"{sha256}  {zip_path.name}\n")
    print(f"  Checksum appended to: {sha_path}")


if __name__ == "__main__":
    main()
