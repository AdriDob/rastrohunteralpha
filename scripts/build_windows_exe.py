"""Build Rastro Windows EXE using Windows Python via WSL interop.

Copies project files to Windows temp, runs PyInstaller via Windows Python,
copies the resulting EXE back to the WSL dist/ directory.
"""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/adrie/projects/Rastro").resolve()
WIN_PYTHON_WSL = "/mnt/c/Users/adrie/AppData/Local/Programs/Python/Python312/python.exe"
WIN_TEMP = r"C:\Users\adrie\AppData\Local\Temp\rastro_build"

EXCLUDED_DIRS = {
    "__pycache__", ".git", "node_modules", ".venv", "build",
    "android", "mobile", "installer", "launcher",
    "targets", "tests", "project_management", "scripts",
    "docs", "logs", "tmp", "dist", ".cursorrules",
}

INCLUDED_DIRS = {
    "desktop", "api", "core_engines", "database", "ai",
}

def copy_project_to_windows():
    dest = Path(WIN_TEMP)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    for d in INCLUDED_DIRS:
        src = ROOT / d
        if src.is_dir():
            shutil.copytree(src, dest / d, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            print(f"  Copied {d}/")

    # Frontend dist
    frontend_dist = ROOT / "frontend" / "dist"
    if frontend_dist.is_dir():
        shutil.copytree(frontend_dist, dest / "frontend" / "dist")
        print("  Copied frontend/dist/")

    # Root-level Python files
    for f in ROOT.glob("*.py"):
        if f.name != "setup.py":
            shutil.copy2(f, dest / f.name)
            print(f"  Copied {f.name}")

    # Rastro.spec
    spec = ROOT / "Rastro.spec"
    if spec.exists():
        shutil.copy2(spec, dest / "Rastro.spec")
        print("  Copied Rastro.spec")

    # .env if exists
    env = ROOT / ".env"
    if env.exists():
        shutil.copy2(env, dest / ".env")

    print(f"\nProject copied to {dest}")


def run_pyinstaller():
    win_path = WIN_TEMP.replace("C:", "C$").replace("\\", "/")
    wsl_path = f"/mnt/c/Users/adrie/AppData/Local/Temp/rastro_build"

    script_path_wsl = Path(wsl_path) / "run_pyinstaller.py"
    script_path_wsl.write_text(f"""
import sys
sys.path.insert(0, r'{WIN_TEMP}')
sys.path.insert(0, r'{WIN_TEMP}\\\\desktop')
import PyInstaller.__main__
PyInstaller.__main__.run([
    '--onedir',
    '--name', 'Rastro',
    '--distpath', r'{WIN_TEMP}\\\\dist',
    '--workpath', r'{WIN_TEMP}\\\\build',
    '--specpath', r'{WIN_TEMP}',
    '--add-data', r'{WIN_TEMP}\\\\frontend\\\\dist;frontend_dist',
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
    r'{WIN_TEMP}\\\\desktop\\\\main_desktop.py',
])
""")

    result = subprocess.run(
        [WIN_PYTHON_WSL, f"{WIN_TEMP}\\\\run_pyinstaller.py"],
        capture_output=True, text=False, timeout=600,
        cwd=WIN_TEMP
    )
    print(result.stdout.decode("cp850", errors="replace")[-5000:] if len(result.stdout) > 5000 else result.stdout.decode("cp850", errors="replace"))
    if result.stderr:
        print("STDERR:", result.stderr.decode("cp850", errors="replace")[-2000:] if len(result.stderr) > 2000 else result.stderr.decode("cp850", errors="replace"))
    return result.returncode


def copy_exe_back():
    exe_dir = Path(WIN_TEMP) / "dist" / "Rastro"
    dest = ROOT / "dist" / "release" / "Rastro-Desktop-1.5.0"
    if exe_dir.exists():
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(exe_dir, dest)
        print(f"EXE copied to {dest}")
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

    print("\n=== Step 3: Copy EXE back to WSL dist ===")
    copy_exe_back()

    print("\nDone!")
