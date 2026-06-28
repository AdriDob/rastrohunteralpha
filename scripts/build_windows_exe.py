#!/usr/bin/env python3
"""Build Rastro Windows EXE using Windows Python via WSL interop.

Usage:
    python scripts/build_windows_exe.py
    python scripts/build_windows_exe.py --python-path "/mnt/c/Python312/python.exe"
    python scripts/build_windows_exe.py --output-dir "/mnt/c/Users/me/Desktop"
    python scripts/build_windows_exe.py --keep-temp

This script:
1. Copies the project to a Windows temp directory
2. Runs PyInstaller via Windows Python (WSL interop)
3. Copies the resulting EXE to --output-dir (if specified)
4. Cleans up the temp directory (unless --keep-temp)

Prerequisites:
  - Windows Python 3.12+ installed (default: /mnt/c/.../Python312/python.exe)
  - PyInstaller installed in Windows Python: pip install pyinstaller
  - Frontend must be built: cd frontend && npm ci && npm run build
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_WIN_PYTHON = "/mnt/c/Users/adrie/AppData/Local/Programs/Python/Python312/python.exe"
DEFAULT_TEMP_NAME = "rastro_build"

INCLUDED_DIRS = {"desktop", "api", "core_engines", "database"}


def resolve_wsl_path(windows_path: str) -> Path:
    """Convert a Windows path like C:\\Users\\... to WSL path /mnt/c/Users/..."""
    wsl = windows_path.replace("\\", "/")
    if ":" in wsl:
        drive = wsl[0].lower()
        wsl = f"/mnt/{drive}{wsl[2:]}"
    return Path(wsl)


def copy_project(wsl_temp: Path) -> None:
    """Copy project source files to the WSL-accessible temp directory."""
    wsl_temp.mkdir(parents=True, exist_ok=True)

    for d in INCLUDED_DIRS:
        src = ROOT / d
        if src.is_dir():
            dst = wsl_temp / d
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    for f in ROOT.glob("*.py"):
        if f.name != "setup.py":
            shutil.copy2(f, wsl_temp / f.name)

    for name in ("Rastro.spec", ".env"):
        src_path = ROOT / name
        if src_path.exists() and not (wsl_temp / name).exists():
            shutil.copy2(src_path, wsl_temp / name)

    # Frontend dist (must be pre-built)
    frontend_src = ROOT / "frontend" / "dist"
    frontend_dst = wsl_temp / "frontend" / "dist"
    if frontend_src.is_dir() and (frontend_src / "index.html").exists():
        if not frontend_dst.exists():
            frontend_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(frontend_src, frontend_dst)
        print("  Copied frontend/dist/")
    else:
        print("  WARNING: frontend/dist/ not found. Build the frontend first:")
        print("    cd frontend && npm ci && npm run build")
        print("  The build will likely fail without a frontend dist.")

    total = sum(f.stat().st_size for f in wsl_temp.rglob("*") if f.is_file())
    print(f"  Project copied ({total / 1024 / 1024:.1f} MB)")


def run_pyinstaller(win_python: str, win_temp: str) -> int:
    """Generate and execute an inline PyInstaller script on Windows Python."""
    pyinstaller_script = f'''
import sys, os
_BASE = r"{win_temp}"
sys.path.insert(0, _BASE)
sys.path.insert(0, os.path.join(_BASE, 'desktop'))
import PyInstaller.__main__
PyInstaller.__main__.run([
    '-y',
    '--onedir',
    '--name', 'Rastro',
    '--distpath', os.path.join(_BASE, 'dist'),
    '--workpath', os.path.join(_BASE, 'build'),
    '--specpath', _BASE,
    '--add-data', os.path.join(_BASE, 'frontend', 'dist') + ';frontend_dist',
    '--hidden-import', 'desktop.main_desktop',
    '--hidden-import', 'desktop.settings',
    '--hidden-import', 'desktop.autostart',
    '--hidden-import', 'desktop.browser_opener',
    '--hidden-import', 'desktop.notifications',
    '--hidden-import', 'desktop.tray',
    '--hidden-import', 'desktop.serve_frontend',
    '--hidden-import', 'desktop.first_run',
    '--hidden-import', 'api.main',
    '--hidden-import', 'api.routers',
    '--hidden-import', 'database.models',
    '--hidden-import', 'uvicorn',
    '--hidden-import', 'uvicorn.logging',
    '--hidden-import', 'uvicorn.loops.auto',
    '--hidden-import', 'uvicorn.protocols.http.auto',
    '--hidden-import', 'uvicorn.protocols.websockets.auto',
    '--hidden-import', 'httpx',
    '--hidden-import', 'sniffio',
    '--hidden-import', 'h11',
    '--hidden-import', 'anyio',
    '--hidden-import', 'pydantic',
    '--collect-all', 'core_engines',
    '--collect-all', 'api',
    '--collect-all', 'database',
    os.path.join(_BASE, 'run.py'),
])
'''

    # Write the script via WSL path, reference it via Windows path
    wsl_temp = resolve_wsl_path(win_temp)
    script_path = wsl_temp / "run_pyinstaller.py"
    script_path.write_text(pyinstaller_script)

    win_script = f"{win_temp}\\run_pyinstaller.py"
    print("  Running PyInstaller (this may take several minutes)...")
    result = subprocess.run(
        [win_python, win_script],
        capture_output=True, text=False, timeout=600,
    )

    out = result.stdout.decode("cp850", errors="replace")
    err = result.stderr.decode("cp850", errors="replace")

    if len(out) > 5000:
        print(out[-5000:])
    else:
        print(out)
    if err:
        print("STDERR:", err[-2000:] if len(err) > 2000 else err)

    return result.returncode


def copy_output(wsl_temp: Path, output_dir: Path) -> bool:
    """Copy the built EXE to the specified output directory."""
    exe_dir = wsl_temp / "dist" / "Rastro"
    if not exe_dir.exists():
        print(f"  ERROR: Build output not found at {exe_dir}")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / "Rastro"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(exe_dir, dest)
    print(f"  Output copied to {dest}")

    total_bytes = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
    print(f"  Total size: {total_bytes / 1024 / 1024:.1f} MB")
    return True


def clean_temp(wsl_temp: Path) -> None:
    """Remove the temporary build directory."""
    if wsl_temp.exists():
        shutil.rmtree(wsl_temp)
        print(f"  Temp directory cleaned: {wsl_temp}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Rastro Windows EXE via WSL interop",
    )
    parser.add_argument(
        "--python-path",
        default=DEFAULT_WIN_PYTHON,
        help=f"Path to Windows Python executable (default: {DEFAULT_WIN_PYTHON})",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Copy the built EXE to this directory (e.g., /mnt/c/Users/me/Desktop)",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep the temporary build directory after completion",
    )
    args = parser.parse_args()

    win_python = args.python_path
    win_temp = f"C:\\Users\\{os.environ.get('USER', 'user')}\\AppData\\Local\\Temp\\{DEFAULT_TEMP_NAME}"
    wsl_temp = resolve_wsl_path(win_temp)

    # Verify Windows Python exists
    win_python_wsl = resolve_wsl_path(win_python)
    if not win_python_wsl.exists():
        print(f"ERROR: Windows Python not found at {win_python}")
        print("Specify the correct path with --python-path")
        sys.exit(1)

    print("=== Rastro Windows Build ===")
    print(f"  Project root: {ROOT}")
    print(f"  Windows Python: {win_python}")
    print(f"  Temp directory: {win_temp}")

    print("\n[1/3] Copying project to Windows temp...")
    copy_project(wsl_temp)

    print("\n[2/3] Running PyInstaller on Windows Python...")
    rc = run_pyinstaller(win_python, win_temp)
    if rc != 0:
        print(f"\nPyInstaller failed (rc={rc})")
        print("Check the output above for errors.")
        if not args.keep_temp:
            clean_temp(wsl_temp)
        sys.exit(1)

    print("\n[3/3] Handling output...")
    if args.output_dir:
        output_path = Path(args.output_dir).resolve()
        copy_output(wsl_temp, output_path)
    else:
        print("  --output-dir not specified; EXE remains in temp directory:")
        print(f"    {wsl_temp / 'dist' / 'Rastro'}")

    if not args.keep_temp:
        clean_temp(wsl_temp)
    else:
        print(f"  Temp directory preserved: {wsl_temp}")

    print("\nBuild completed successfully!")


if __name__ == "__main__":
    main()
