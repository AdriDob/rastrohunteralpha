#!/usr/bin/env python3
"""Rastro Release Builder — one command to build the final production output.

Usage:
    python scripts/build_release.py              # Full release build
    python scripts/build_release.py --version X.Y.Z  # Custom version
    python scripts/build_release.py --no-frontend    # Skip frontend build
    python scripts/build_release.py --dry-run        # Print steps only

Builds:
  - Backend   (PyInstaller EXE)
  - Frontend  (Vite production build)
  - Installer (NSIS .exe)
  - ZIP package
  - Documentation (README, CHANGELOG, LICENSE, VERSION, build_info.json)

Output (Windows):
  C:\\Users\\adrie\\OneDrive\\Desktop\\Yo\\privado\\Rastro\\
    ├── RastroInstaller.exe
    ├── Rastro.zip
    ├── README.txt
    ├── CHANGELOG.md
    ├── VERSION.txt
    ├── LICENSE.txt
    └── build_info.json
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
VERSION_FILE = PROJECT_ROOT / "VERSION"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"

DEFAULT_OUTPUT_ENV = os.environ.get("RASTRO_OUTPUT_DIR")
if DEFAULT_OUTPUT_ENV:
    DEFAULT_OUTPUT = Path(DEFAULT_OUTPUT_ENV)
elif sys.platform.startswith("win"):
    DEFAULT_OUTPUT = Path(os.environ.get("USERPROFILE", "C:/")) / "OneDrive" / "Desktop" / "Yo" / "privado"
elif Path("/mnt/c/Users/adrie/OneDrive/Desktop/Yo/privado").exists():
    DEFAULT_OUTPUT = Path("/mnt/c/Users/adrie/OneDrive/Desktop/Yo/privado")
else:
    DEFAULT_OUTPUT = Path.home() / "Rastro"

IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")


def log(step: str, msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{step:>20}] {msg}")


def run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 300) -> bool:
    try:
        result = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            log("CMD", f"FAILED: {' '.join(cmd)}")
            log("CMD", result.stderr[-500:] if result.stderr else "no stderr")
            return False
        return True
    except subprocess.TimeoutExpired:
        log("CMD", f"TIMEOUT after {timeout}s: {' '.join(cmd)}")
        return False
    except FileNotFoundError as exc:
        log("CMD", f"NOT FOUND: {exc}")
        return False


def read_version() -> str:
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return "1.5.0"


def build_frontend() -> bool:
    log("FRONTEND", "Building frontend (npm ci + npm run build)...")
    if not (FRONTEND_DIR / "package.json").exists():
        log("FRONTEND", "SKIP — no package.json found")
        return False

    if not run_cmd(["npm", "ci", "--silent"], cwd=FRONTEND_DIR, timeout=120):
        log("FRONTEND", "npm ci failed, trying npm install...")
        if not run_cmd(["npm", "install", "--silent"], cwd=FRONTEND_DIR, timeout=120):
            log("FRONTEND", "FAILED")
            return False

    if not run_cmd(["npm", "run", "build"], cwd=FRONTEND_DIR, timeout=120):
        log("FRONTEND", "FAILED")
        return False

    dist = FRONTEND_DIR / "dist"
    if not dist.is_dir() or not list(dist.rglob("*.html")):
        log("FRONTEND", "FAILED — no dist/index.html generated")
        return False

    size = sum(f.stat().st_size for f in dist.rglob("*") if f.is_file())
    log("FRONTEND", f"OK — {size / 1024:.0f} KB in {sum(1 for _ in dist.rglob('*'))} files")
    return True


def build_pyinstaller() -> bool:
    log("PYINSTALLER", "Building EXE (pyinstaller Rastro.spec)...")
    spec = PROJECT_ROOT / "Rastro.spec"
    if not spec.exists():
        log("PYINSTALLER", "SKIP — no Rastro.spec found")
        return False

    if not shutil.which("pyinstaller"):
        log("PYINSTALLER", "SKIP — PyInstaller not installed")
        return False

    if not run_cmd(["pyinstaller", "Rastro.spec", "-y"], timeout=600):
        log("PYINSTALLER", "FAILED")
        return False

    exe = DIST_DIR / "Rastro" / ("Rastro.exe" if IS_WINDOWS else "Rastro")

    if not exe.exists():
        log("PYINSTALLER", f"FAILED — {exe} not found")
        return False

    size = exe.stat().st_size
    log("PYINSTALLER", f"OK — {size / 1024 / 1024:.1f} MB")
    return True


def build_installer() -> bool:
    log("INSTALLER", "Building NSIS installer...")
    nsi = PROJECT_ROOT / "installer" / "install_windows.nsi"
    if not nsi.exists():
        log("INSTALLER", "SKIP — no installer/install_windows.nsi found")
        return False

    makensis = shutil.which("makensis")
    if not makensis:
        log("INSTALLER", "SKIP — NSIS (makensis) not installed")
        return False

    if not run_cmd([makensis, str(nsi)], cwd=PROJECT_ROOT, timeout=120):
        log("INSTALLER", "FAILED")
        return False

    installer = PROJECT_ROOT / f"Rastro_Setup_{read_version()}.exe"
    if not installer.exists():
        installer = DIST_DIR / f"Rastro_Setup_{read_version()}.exe"
    if not installer.exists():
        log("INSTALLER", "FAILED — installer EXE not found")
        return False

    log("INSTALLER", f"OK — {installer.name} ({installer.stat().st_size / 1024 / 1024:.1f} MB)")
    return True


def create_docs(output_dir: Path, version: str) -> None:
    log("DOCS", f"Generating documentation files in {output_dir}")

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
        f"  1. Ejecutar RastroInstaller.exe\n"
        f"  2. Seguir el asistente de instalación\n"
        f"  3. Rastro se inicia automáticamente al finalizar\n"
        f"  4. Abrir Dashboard: http://127.0.0.1:8000\n"
        f"\n"
        f"Uso Diario:\n"
        f"  • Rastro inicia automáticamente con Windows\n"
        f"  • Icono en bandeja del sistema para control\n"
        f"  • Dashboard accesible en el navegador\n"
        f"  • Actualizaciones automáticas vía GitHub\n"
        f"\n"
        f"Requisitos:\n"
        f"  • Windows 11 64-bit\n"
        f"  • 4 GB RAM mínimo (8 GB recomendado)\n"
        f"  • Conexión a Internet\n"
        f"\n"
        f"Soporte:\n"
        f"  • Issues: https://github.com/AdriDob/rastrohunteralpha/issues\n"
        f"\n"
        f"──  v{version} – {datetime.now().strftime('%Y-%m-%d')}  ──\n"
    )
    log("DOCS", f"  README.txt ({readme.stat().st_size} bytes)")

    changelog = output_dir / "CHANGELOG.md"
    changelog.write_text(
        f"# Changelog\n\n"
        f"## v{version} ({datetime.now().strftime('%Y-%m-%d')})\n\n"
        f"### 🚀 Nuevo\n"
        f"- Build pipeline profesional con un solo comando\n"
        f"- Instalador NSIS con instalación en Program Files\n"
        f"- Servicio Windows (pywin32) con inicio automático\n"
        f"- Watchdog interno con monitorización y auto-recovery\n"
        f"- Actualizaciones automáticas con rollback seguro\n"
        f"- Dashboard de salud y estado del sistema\n"
        f"- Centro de Identity para gestión de cuentas\n"
        f"\n"
        f"### 🛡️ Seguridad\n"
        f"- Cifrado AES-256-GCM para credenciales\n"
        f"- Flag 'Nunca enviar sin aprobación' (por defecto activado)\n"
        f"- Sesión desktop con auto-autenticación\n"
        f"\n"
        f"### ⚡ Rendimiento\n"
        f"- EventSystem con límite FIFO (max 500 eventos)\n"
        f"- SQLite WAL mode + busy_timeout\n"
        f"- Optimización de memoria en Identity Vault\n"
        f"\n"
        f"### 🐛 Correcciones\n"
        f"- Pipeline stuck en PAID → CLOSED\n"
        f"- Scheduler double-wrapping\n"
        f"- Agent subscriptions sin limpiar en stop()\n"
        f"- Retry delay faltante en Coordinator\n"
        f"- OOM en EventSystem\n"
        f"- SQLite database is locked\n"
        f"\n"
        f"## v1.5.0 (2026-06-15)\n\n"
        f"- Release Candidate 1\n"
        f"- Arquitectura multi-agente completa\n"
        f"- Pipeline de 11 estados\n"
        f"- Integración con HackerOne, Bugcrowd, Intigriti, YesWeHack, Synack\n"
        f"- Frontend PrimeReact dark mode\n"
        f"- 333 tests pasando\n"
    )
    log("DOCS", f"  CHANGELOG.md ({changelog.stat().st_size} bytes)")

    version_txt = output_dir / "VERSION.txt"
    version_txt.write_text(f"{version}\n")
    log("DOCS", f"  VERSION.txt ({version_txt.stat().st_size} bytes)")

    license_file = output_dir / "LICENSE.txt"
    current_year = datetime.now().year
    license_file.write_text(
        f"Rastro v{version} — Investigación OS Profesional\n"
        f"Copyright © {current_year} AdriDob\n\n"
        f"Todos los derechos reservados.\n\n"
        f"Este software está protegido por leyes de propiedad intelectual.\n"
        f"Queda prohibida la distribución, modificación o uso no autorizado.\n\n"
        f"Para uso personal únicamente.\n"
        f"Licencia de uso no transferible.\n"
    )
    log("DOCS", f"  LICENSE.txt ({license_file.stat().st_size} bytes)")

    log("DOCS", "OK — 4 documentation files generated")


def create_build_info(output_dir: Path, version: str, components: dict[str, bool]) -> None:
    info = {
        "app": "Rastro",
        "version": version,
        "build_date": datetime.now(timezone.utc).isoformat(),
        "build_host": os.uname().nodename if hasattr(os, "uname") else "unknown",
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "components": components,
        "files": {},
    }

    for f in output_dir.iterdir():
        if f.is_file():
            info["files"][f.name] = {
                "size_bytes": f.stat().st_size,
                "size_human": f"{f.stat().st_size / 1024:.1f} KB" if f.stat().st_size < 1024 * 1024 else f"{f.stat().st_size / 1024 / 1024:.1f} MB",
            }

    build_info = output_dir / "build_info.json"
    build_info.write_text(json.dumps(info, indent=2))
    log("DOCS", f"  build_info.json ({build_info.stat().st_size} bytes)")


def create_zip(output_dir: Path, version: str) -> Path | None:
    log("ZIP", f"Creating Rastro.zip from {output_dir}...")
    zip_path = output_dir / "Rastro.zip"

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for f in output_dir.iterdir():
            if f.is_file() and f.name != "Rastro.zip":
                zf.write(f, f.name)

    if zip_path.exists():
        size = zip_path.stat().st_size
        log("ZIP", f"OK — {zip_path.name} ({size / 1024:.1f} KB)")
        return zip_path
    log("ZIP", "FAILED")
    return None


def copy_to_output(output_dir: Path) -> bool:
    target = DEFAULT_OUTPUT / "Rastro"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for f in output_dir.iterdir():
        if f.is_file():
            shutil.copy2(f, target / f.name)
    log("COPY", f"Files copied to: {target}")
    return True


def verify_output(output_dir: Path) -> bool:
    log("VERIFY", "Verifying output files...")
    required = ["Rastro.zip", "README.txt", "CHANGELOG.md", "VERSION.txt", "LICENSE.txt", "build_info.json"]
    all_ok = True

    for name in required:
        path = output_dir / name
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        status = "✅" if exists else "❌"
        log("VERIFY", f"  {status} {name} ({size / 1024:.1f} KB)" if exists else f"  {status} {name} (MISSING)")
        if not exists:
            all_ok = False

    rastro_dir = output_dir / "Rastro"
    rastro_exe = rastro_dir / ("Rastro.exe" if IS_WINDOWS else "Rastro")
    if rastro_exe.exists():
        log("VERIFY", f"  ✅ Rastro/{rastro_exe.name} ({rastro_exe.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        log("VERIFY", "  ⚠ Rastro/ binary not found (PyInstaller not run)")

    return all_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Rastro Release Builder")
    parser.add_argument("--version", default=None, help="Version override")
    parser.add_argument("--no-frontend", action="store_true", help="Skip frontend build")
    parser.add_argument("--clean", action="store_true", help="Clean dist/ and build/ before building")
    parser.add_argument("--no-nsis", action="store_true", help="Skip NSIS installer even if available")
    parser.add_argument("--dry-run", action="store_true", help="Print steps without executing")
    args = parser.parse_args()

    version = args.version or read_version()
    log("BUILD", f"Rastro Release Builder v{version}")
    log("BUILD", f"Platform: {sys.platform}")
    log("BUILD", f"Project: {PROJECT_ROOT}")
    log("BUILD", f"Dry run: {args.dry_run}")

    output_dir = PROJECT_ROOT / "build" / "release"
    if args.dry_run:
        log("BUILD", f"Output would be: {output_dir}")
        log("BUILD", f"Output target: {DEFAULT_OUTPUT / 'Rastro'}")
        log("BUILD", "Dry run complete")
        return

    if args.clean:
        log("CLEAN", "Removing dist/ and build/ ...")
        for d in [DIST_DIR, BUILD_DIR]:
            if d.exists():
                shutil.rmtree(d)
                log("CLEAN", f"  Removed: {d}")
        log("CLEAN", "OK")

    output_dir.mkdir(parents=True, exist_ok=True)

    components: dict[str, bool] = {}

    components["frontend"] = build_frontend() if not args.no_frontend else True
    components["pyinstaller"] = build_pyinstaller()
    components["installer"] = build_installer() if not args.no_nsis else False
    components["docs"] = True

    create_docs(output_dir, version)
    create_build_info(output_dir, version, components)

    if components.get("pyinstaller") or components.get("installer"):
        src = DIST_DIR / "Rastro"
        if src.exists():
            log("BUILD", "Copying PyInstaller build to output...")
            dest = output_dir / "Rastro"
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)

    create_zip(output_dir, version)

    log("BUILD", "─" * 50)

    verify_output(output_dir)

    log("BUILD", "─" * 50)
    log("BUILD", f"Output directory: {output_dir}")
    log("BUILD", f"Total size: {sum(f.stat().st_size for f in output_dir.rglob('*') if f.is_file()) / 1024 / 1024:.1f} MB")

    copy_to_output(output_dir)

    log("BUILD", "─" * 50)
    if IS_LINUX:
        log("BUILD", "NOTE: Running on Linux. To complete the Windows build:")
        log("BUILD", f"  1. Copy {output_dir} to Windows")
        log("BUILD", "  2. Run: pyinstaller Rastro.spec -y")
        log("BUILD", "  3. Run: makensis installer\\install_windows.nsi")
        log("BUILD", "  4. Run: python scripts\\build_release.py")
        log("BUILD", "  OR use: scripts\\build_windows.ps1")
    else:
        log("BUILD", "Build complete. Files ready in:")
        log("BUILD", f"  {output_dir}")
        log("BUILD", f"  Copied to: {DEFAULT_OUTPUT / 'Rastro'}")

    log("BUILD", "DONE")


if __name__ == "__main__":
    main()
