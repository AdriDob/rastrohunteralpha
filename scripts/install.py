#!/usr/bin/env python3
"""Rastro install script — one-command install without NSIS.

Usage:
    python scripts/install.py              # Full install (recommended)
    python scripts/install.py --dev         # Dev mode (skip PyInstaller)
    python scripts/install.py --portable    # Portable ZIP only
    python scripts/install.py --output PATH # Custom output directory
    python scripts/install.py --no-frontend # Skip frontend build

Output (default):
  C:\\Users\\<user>\\OneDrive\\Desktop\\Yo\\privado\\Rastro\\
    ├── Rastro.exe              (PyInstaller binary)
    ├── frontend_dist/          (Vite production build)
    ├── Rastro.zip              (Portable ZIP)
    ├── README.txt
    ├── CHANGELOG.md
    ├── VERSION.txt
    ├── LICENSE.txt
    ├── build_info.json
    └── install_log.txt
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DIST_DIR = PROJECT_ROOT / "dist"
VERSION_FILE = PROJECT_ROOT / "VERSION"
MIN_PYTHON = (3, 10)


def log(step: str, msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{step:>20}] {msg}")


def read_version() -> str:
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return "1.6.0"


def get_default_output() -> Path:
    env = os.environ.get("RASTRO_OUTPUT_DIR")
    if env:
        return Path(env)
    if sys.platform == "win32":
        return Path(os.environ.get("USERPROFILE", "C:/")) / "OneDrive" / "Desktop" / "Yo" / "privado" / "Rastro"
    if sys.platform.startswith("linux"):
        return Path.home() / "Rastro"
    return PROJECT_ROOT / "dist" / "install"


def run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 300) -> bool:
    try:
        result = subprocess.run(
            cmd, cwd=cwd or PROJECT_ROOT,
            capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            log("CMD", f"FAILED: {' '.join(cmd)}")
            stderr = result.stderr.strip()
            if stderr:
                log("CMD", stderr[-500:])
            return False
        return True
    except FileNotFoundError:
        log("CMD", f"NOT FOUND: {cmd[0]} — is it installed?")
        return False
    except subprocess.TimeoutExpired:
        log("CMD", f"TIMEOUT after {timeout}s: {' '.join(cmd)}")
        return False
    except Exception as exc:
        log("CMD", f"ERROR: {exc}")
        return False


# ── Step 1: Frontend ──────────────────────────────────────────────────

def ensure_frontend_built() -> bool:
    dist = FRONTEND_DIR / "dist"
    if dist.is_dir() and list(dist.rglob("*.html")):
        log("FRONTEND", "Already built — skipping")
        return True
    log("FRONTEND", "Building frontend...")
    if not (FRONTEND_DIR / "package.json").exists():
        log("FRONTEND", "SKIP — no frontend/package.json found")
        return False
    if not run_cmd(["npm", "ci", "--silent"], FRONTEND_DIR, 120):
        log("FRONTEND", "npm ci failed — trying npm install...")
        if not run_cmd(["npm", "install", "--silent"], FRONTEND_DIR, 120):
            log("FRONTEND", "FAILED")
            return False
    if not run_cmd(["npm", "run", "build"], FRONTEND_DIR, 120):
        log("FRONTEND", "FAILED")
        return False
    log("FRONTEND", "OK")
    return True


# ── Step 2: PyInstaller ───────────────────────────────────────────────

def build_pyinstaller() -> bool:
    log("PYINSTALLER", "Building EXE...")
    spec = PROJECT_ROOT / "Rastro.spec"
    if not spec.exists():
        log("PYINSTALLER", "SKIP — no Rastro.spec found")
        return False
    if not shutil.which("pyinstaller"):
        log("PYINSTALLER", "SKIP — PyInstaller not installed (install with: pip install pyinstaller)")
        return False
    if not run_cmd(["pyinstaller", "Rastro.spec", "-y"], timeout=600):
        log("PYINSTALLER", "FAILED")
        return False
    exe_name = "Rastro.exe" if sys.platform == "win32" else "Rastro"
    exe = DIST_DIR / "Rastro" / exe_name
    if not exe.exists():
        log("PYINSTALLER", f"FAILED — {exe} not found")
        return False
    log("PYINSTALLER", f"OK — {exe.stat().st_size / 1024 / 1024:.1f} MB")
    return True


# ── Step 3: Assemble output ───────────────────────────────────────────

def assemble_output(output_dir: Path, version: str, dev_mode: bool) -> None:
    log("ASSEMBLE", f"Output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # PyInstaller build
    pyinstaller_src = DIST_DIR / "Rastro"
    if pyinstaller_src.exists() and not dev_mode:
        dest = output_dir / "Rastro"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(pyinstaller_src, dest)
        size_mb = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file()) / 1024 / 1024
        log("ASSEMBLE", f"  Rastro/ — {size_mb:.1f} MB")
    else:
        log("ASSEMBLE", "  Rastro/ — skipped (dev mode or not built)")

    # Frontend dist
    frontend_src = FRONTEND_DIR / "dist"
    if frontend_src.exists():
        dest = output_dir / "frontend_dist"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(frontend_src, dest)
        size_kb = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file()) / 1024
        log("ASSEMBLE", f"  frontend_dist/ — {size_kb:.0f} KB")

    # Docs
    _write_docs(output_dir, version)

    # build_info.json
    _write_build_info(output_dir, version, dev_mode)

    # install_log.txt
    _write_install_log(output_dir, version)

    log("ASSEMBLE", "OK")


def _write_docs(output_dir: Path, version: str) -> None:
    readme = output_dir / "README.txt"
    readme.write_text(
        f"═══════════════════════════════════════════\n"
        f"  Rastro v{version} — Investigación OS Profesional\n"
        f"═══════════════════════════════════════════\n"
        f"\n"
        f"• Dashboard:      http://127.0.0.1:8000\n"
        f"• Documentación:  https://github.com/AdriDob/rastrohunteralpha\n"
        f"• Licencia:       LICENSE.txt\n"
        f"\n"
        f"─═─═─═─═─═─═─═─═─═─═─═─═─═─═─═─═─═─═─═─═─═─═\n"
        f"\n"
        f"Instalación:\n"
        f"  1. Ejecutar Rastro.exe\n"
        f"  2. Rastro se inicia automáticamente\n"
        f"  3. Abrir Dashboard: http://127.0.0.1:8000\n"
        f"\n"
        f"Uso Diario:\n"
        f"  • Rastro inicia automáticamente con Windows\n"
        f"  • Icono en bandeja del sistema para control\n"
        f"  • Dashboard accesible en el navegador\n"
        f"\n"
        f"Requisitos:\n"
        f"  • Windows 11 64-bit\n"
        f"  • 4 GB RAM mínimo (8 GB recomendado)\n"
        f"  • Conexión a Internet\n"
        f"\n"
        f"──  v{version} – {datetime.now().strftime('%Y-%m-%d')}  ──\n"
    )
    log("DOCS", f"  README.txt ({readme.stat().st_size} bytes)")

    changelog = output_dir / "CHANGELOG.md"
    changelog.write_text(
        f"# Changelog\n\n"
        f"## v{version} ({datetime.now().strftime('%Y-%m-%d')})\n\n"
        f"### 🚀 Nuevo\n"
        f"- Instalación con un solo comando (python scripts/install.py)\n"
        f"- Auto-build de frontend y backend\n"
        f"- Validación post-instalación\n"
        f"- Modo portable sin instalación\n"
        f"\n"
        f"### 🛡️ Seguridad\n"
        f"- Cifrado AES-256-GCM para credenciales\n"
        f"- Sesión desktop con auto-autenticación\n"
        f"\n"
        f"### ⚡ Rendimiento\n"
        f"- EventSystem con límite FIFO (max 500 eventos)\n"
        f"- SQLite WAL mode + busy_timeout\n"
        f"- Watchdog con auto-recovery\n"
        f"\n"
    )
    log("DOCS", f"  CHANGELOG.md ({changelog.stat().st_size} bytes)")

    version_txt = output_dir / "VERSION.txt"
    version_txt.write_text(f"{version}\n")
    log("DOCS", f"  VERSION.txt ({version_txt.stat().st_size} bytes)")

    current_year = datetime.now().year
    license_file = output_dir / "LICENSE.txt"
    license_file.write_text(
        f"Rastro v{version} — Investigación OS Profesional\n"
        f"Copyright © {current_year} AdriDob\n\n"
        f"Todos los derechos reservados.\n\n"
        f"Para uso personal únicamente.\n"
        f"Licencia de uso no transferible.\n"
    )
    log("DOCS", f"  LICENSE.txt ({license_file.stat().st_size} bytes)")


def _write_build_info(output_dir: Path, version: str, dev_mode: bool) -> None:
    info = {
        "app": "Rastro",
        "version": version,
        "build_date": datetime.now(timezone.utc).isoformat(),
        "build_host": os.uname().nodename if hasattr(os, "uname") else "unknown",
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "mode": "dev" if dev_mode else "production",
        "files": {},
    }
    for f in output_dir.iterdir():
        if f.is_file():
            size = f.stat().st_size
            info["files"][f.name] = {
                "size_bytes": size,
                "size_human": f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB",
            }
    build_info = output_dir / "build_info.json"
    build_info.write_text(json.dumps(info, indent=2))
    log("DOCS", f"  build_info.json ({build_info.stat().st_size} bytes)")


def _write_install_log(output_dir: Path, version: str) -> None:
    log_file = output_dir / "install_log.txt"
    lines = [
        f"Rastro v{version} — Install Log",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Platform: {sys.platform}",
        f"Python: {sys.version}",
        f"Output: {output_dir}",
        "",
    ]
    log_file.write_text("\n".join(lines))
    log("DOCS", f"  install_log.txt ({log_file.stat().st_size} bytes)")


# ── Step 4: Portable ZIP ────────────────────────────────────────────

def create_portable_zip(output_dir: Path, version: str) -> Path | None:
    log("ZIP", "Creating Rastro.zip...")
    zip_path = output_dir / "Rastro.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for root, _dirs, files in os.walk(output_dir):
            for file in files:
                if file == "Rastro.zip":
                    continue
                full_path = Path(root) / file
                arcname = str(full_path.relative_to(output_dir.parent))
                zf.write(full_path, arcname)

    if zip_path.exists():
        log("ZIP", f"OK — {zip_path.name} ({zip_path.stat().st_size / 1024:.1f} KB)")
        return zip_path
    log("ZIP", "FAILED")
    return None


# ── Step 5: Validation ──────────────────────────────────────────────

def validate_installation(output_dir: Path) -> bool:
    log("VALIDATE", "Verifying installation...")
    all_ok = True

    checks: list[tuple[str, bool]] = [
        ("README.txt", (output_dir / "README.txt").exists()),
        ("CHANGELOG.md", (output_dir / "CHANGELOG.md").exists()),
        ("VERSION.txt", (output_dir / "VERSION.txt").exists()),
        ("LICENSE.txt", (output_dir / "LICENSE.txt").exists()),
        ("build_info.json", (output_dir / "build_info.json").exists()),
        ("frontend_dist/index.html", (output_dir / "frontend_dist" / "index.html").exists()),
        ("Rastro.exe", (output_dir / "Rastro" / "Rastro.exe").exists()),
    ]

    for name, ok in checks:
        status = "OK" if ok else "MISSING"
        log("VALIDATE", f"  [{status:>7}] {name}")
        if not ok:
            all_ok = False

    if all_ok:
        log("VALIDATE", "All checks passed")
    else:
        log("VALIDATE", "Some files missing — install may be incomplete")
    return all_ok


# ── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Rastro installer — one-command setup")
    parser.add_argument("--dev", action="store_true", help="Dev mode (skip PyInstaller, use python run.py)")
    parser.add_argument("--portable", action="store_true", help="Portable ZIP only (no output dir assembly)")
    parser.add_argument("--output", type=Path, default=None, help="Output directory (default: RASTRO_OUTPUT_DIR or platform default)")
    parser.add_argument("--no-frontend", action="store_true", help="Skip frontend build")
    parser.add_argument("--version", default=None, help="Version override")
    args = parser.parse_args()

    version = args.version or read_version()
    output_dir = (args.output or get_default_output()).resolve()

    log("INSTALL", f"Rastro v{version} — Installer")
    log("INSTALL", f"Platform: {sys.platform}")
    log("INSTALL", f"Mode: {'dev' if args.dev else 'portable' if args.portable else 'production'}")
    log("INSTALL", f"Output: {output_dir}")

    if sys.version_info < MIN_PYTHON:
        log("INSTALL", f"ERROR: Python {'.'.join(str(v) for v in MIN_PYTHON)}+ required")
        sys.exit(1)

    # Step 1: Frontend
    if not args.no_frontend:
        ensure_frontend_built()

    # Step 2: PyInstaller
    pyinstaller_ok = False
    if not args.dev:
        pyinstaller_ok = build_pyinstaller()
        if not pyinstaller_ok and not args.portable:
            log("INSTALL", "PyInstaller build failed — falling back to dev mode")
            args.dev = True

    # Step 3: Portable ZIP mode (exit early)
    if args.portable:
        if pyinstaller_ok:
            create_portable_zip(DIST_DIR / "Rastro", version)
        elif DIST_DIR.exists():
            log("PORTABLE", "No PyInstaller build — creating source portable instead")
        log("INSTALL", "Portable mode complete")
        return

    # Step 4: Assemble output
    assemble_output(output_dir, version, args.dev)

    # Step 5: Portable ZIP
    create_portable_zip(output_dir, version)

    # Step 6: Validate
    validate_installation(output_dir)

    # Summary
    log("INSTALL", "─" * 50)
    log("INSTALL", f"Install complete: {output_dir}")
    total_mb = sum(f.stat().st_size for f in output_dir.rglob("*") if f.is_file()) / 1024 / 1024
    log("INSTALL", f"Total size: {total_mb:.1f} MB")
    log("INSTALL", f"Run: {output_dir / 'Rastro' / 'Rastro.exe'}")
    log("INSTALL", "DONE")


if __name__ == "__main__":
    main()
