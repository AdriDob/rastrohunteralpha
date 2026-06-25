"""Build Rastro Windows EXE using Windows Python via WSL interop.

Copies project files to Windows temp, runs PyInstaller via Windows Python,
copies the resulting EXE to the diagnostic folder on OneDrive.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/adrie/projects/Rastro").resolve()
WIN_PYTHON_WSL = "/mnt/c/Users/adrie/AppData/Local/Programs/Python/Python312/python.exe"

# WSL paths (used for file operations from Linux)
WSL_TEMP = Path("/mnt/c/Users/adrie/AppData/Local/Temp/rastro_build")
# Windows paths (used when calling Windows executables)
WIN_TEMP = r"C:\Users\adrie\AppData\Local\Temp\rastro_build"

INCLUDED_DIRS = {"desktop", "api", "core_engines", "database", "ai"}

def copy_project_to_windows():
    dest = WSL_TEMP
    dest.mkdir(parents=True, exist_ok=True)

    for d in INCLUDED_DIRS:
        src = ROOT / d
        if src.is_dir():
            dst = dest / d
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for f in ROOT.glob("*.py"):
        if f.name != "setup.py":
            shutil.copy2(f, dest / f.name)
    for name, src_path in [("Rastro.spec", ROOT / "Rastro.spec"), (".env", ROOT / ".env")]:
        if src_path.exists() and not (dest / name).exists():
            shutil.copy2(src_path, dest / name)
    frontend_src = ROOT / "frontend" / "dist"
    frontend_dst = dest / "frontend" / "dist"
    if frontend_src.is_dir() and not frontend_dst.is_dir():
        frontend_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(frontend_src, frontend_dst)
        print("  Copied frontend/dist/")
    print(f"  Source files synced (build cache preserved)")


def run_pyinstaller():
    pyinstaller_script = f"""
import sys, os
_BASE = r"{WIN_TEMP}"
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
    '--collect-all', 'ai',
    os.path.join(_BASE, 'run.py'),
])
"""
    script_path = WSL_TEMP / "run_pyinstaller.py"
    script_path.write_text(pyinstaller_script)

    win_script = WIN_TEMP + r"\run_pyinstaller.py"
    result = subprocess.run(
        [WIN_PYTHON_WSL, win_script],
        capture_output=True, text=False, timeout=600,
    )
    out = result.stdout.decode("cp850", errors="replace")
    err = result.stderr.decode("cp850", errors="replace")
    # Print last 5000 chars of stdout
    if len(out) > 5000:
        print(out[-5000:])
    else:
        print(out)
    if err:
        print("STDERR:", err[-2000:] if len(err) > 2000 else err)
    return result.returncode


def copy_exe_to_diagnostics():
    exe_dir = WSL_TEMP / "dist" / "Rastro"
    dest_diag = Path("/mnt/c/Users/adrie/OneDrive/Desktop/Yo/privado/Rastro-DIAG")
    if exe_dir.exists():
        if dest_diag.exists():
            shutil.rmtree(dest_diag)
        shutil.copytree(exe_dir, dest_diag)
        print(f"\nDiagnostic EXE copied to {dest_diag}")
        # Show size
        total_bytes = sum(
            f.stat().st_size for f in dest_diag.rglob("*") if f.is_file()
        )
        print(f"Total size: {total_bytes / 1024 / 1024:.1f} MB")
        return True
    else:
        print("EXE not found at", exe_dir)
        return False


if __name__ == "__main__":
    print("=== Step 1: Copy project to Windows temp ===")
    copy_project_to_windows()

    print("\n=== Step 2: Run PyInstaller on Windows Python ===")
    rc = run_pyinstaller()
    if rc != 0:
        print(f"\nPyInstaller failed (rc={rc})")
        sys.exit(1)

    print("\n=== Step 3: Copy diagnostic EXE to OneDrive ===")
    copy_exe_to_diagnostics()

    print("\nDone!")
