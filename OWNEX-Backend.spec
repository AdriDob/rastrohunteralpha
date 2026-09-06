# -*- mode: python ; coding: utf-8 -*-
# ruff: noqa
#
# OWNEX Backend — PyInstaller build spec for standalone FastAPI sidecar.
# Entrypoint: src-tauri/binaries/start_backend.py
# Output: dist/ownex-backend  (ONEFILE — self-contained)
#
# ONEFILE is required by the Tauri externalBin contract: Tauri bundles and
# spawns exactly one file per target triple. A ONEDIR exe copied without its
# _internal/ directory cannot import api.main (the failure that shipped in
# the 2026-08-24 MSI). First launch extracts to %TEMP% (~10-30 s), which fits
# inside lib.rs's health-poll budget.
#
# Build with:
#   pyinstaller OWNEX-Backend.spec --clean --noconfirm
#
# CLI args (passed by Tauri sidecar):
#   --port <port>       (default: 8000)
#   --host <host>       (default: 127.0.0.1)
#   --data-dir <path>   (default: %LOCALAPPDATA%\OWNEX on Windows)
#   --log-level <level> (default: INFO)

import os
import fnmatch
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.getcwd()).resolve()
IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS = sys.platform == "darwin"

# ── Auto-discover router modules ─────────────────────────────────────
ROUTERS_DIR = PROJECT_ROOT / "api" / "routers"
router_modules = []
if ROUTERS_DIR.is_dir():
    for f in sorted(ROUTERS_DIR.iterdir()):
        if f.suffix == ".py" and f.stem != "__init__":
            router_modules.append(f"api.routers.{f.stem}")

# ── Auto-discover cores subpackages ──────────────────────────────────
CORE_DIR = PROJECT_ROOT / "cores"
core_packages = []
if CORE_DIR.is_dir():
    for d in sorted(CORE_DIR.iterdir()):
        if d.is_dir() and (d / "__init__.py").exists() and d.stem != "__pycache__":
            core_packages.append(f"cores.{d.stem}")

# ── Hidden imports ────────────────────────────────────────────────────
HIDDEN_IMPORTS = [
    # Entrypoint
    "src-tauri.binaries.start_backend",
    # API layer
    "api", "api.main", *router_modules,
    # Database
    "database", "database.db", "database.models",
    # Core engines
    "cores", "cores.env", "cores.env.config",
    "cores.platform", "cores.platform.system",
    "cores.log_config", "cores.observability",
    *core_packages,
    # Web server
    "uvicorn", "uvicorn.logging", "uvicorn.loops", "uvicorn.loops.auto",
    "uvicorn.protocols", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    # HTTP / networking
    "httpx", "sniffio", "h11", "anyio",
    # Config / serialization
    "pydantic", "pydantic_settings",
    # Form parsing — MUST be present: FastAPI Form() endpoints fail at
    # runtime without it. As a hiddenimport its absence breaks the BUILD
    # loudly instead of being swallowed by collect_all's try/except.
    "python_multipart", "numpy",
    # Database ORM
    "sqlalchemy",
    # Metrics
    "prometheus_client",
    # Async runtime
    "asyncio",
]

# ── Collect data from packages ────────────────────────────────────────
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []

for pkg in ("api", "database", "core", "cores"):
    pkg_dir = PROJECT_ROOT / pkg
    if pkg_dir.is_dir():
        tmp = collect_all(pkg)
        datas += tmp[0]
        binaries += tmp[1]
        HIDDEN_IMPORTS += tmp[2]

# Third-party packages
for pkg in (
    "fastapi", "starlette", "pydantic", "pydantic_settings",
    "sqlalchemy", "aiosqlite", "httpx",
    "prometheus_client", "jinja2", "python_multipart", "numpy",
    "sse_starlette", "websockets",
):
    try:
        tmp = collect_all(pkg)
        datas += tmp[0]
        binaries += tmp[1]
        HIDDEN_IMPORTS += tmp[2]
    except Exception:
        pass

# Include VERSION file
version_file = PROJECT_ROOT / "VERSION"
if version_file.exists():
    datas.append((str(version_file), "."))

# ── Exclude runtime DB files ──────────────────────────────────────────
_filtered = []
for src, dest in datas:
    if any(fnmatch.fnmatch(src, p) for p in (
        "*catseye.db*", "*.db-wal", "*.db-shm",
        "*.sqlite*", "*.db-journal",
    )):
        continue
    _filtered.append((src, dest))
datas = _filtered

# ── Excludes ──────────────────────────────────────────────────────────
EXCLUDES = [
    "matplotlib", "scipy", "notebook", "jupyter",
    "PyQt5", "PyQt6", "PySide2", "PySide6",
    "tkinter",
]

# ── Analysis ──────────────────────────────────────────────────────────
a = Analysis(
    ["src-tauri/binaries/start_backend.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=HIDDEN_IMPORTS,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# Output name without extension (Tauri expects base name without platform suffix)
EXE_NAME = "ownex-backend"

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=EXE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX off: onefile + UPX is a well-known Windows Defender false-positive
    # trigger; reliability of first launch beats ~25% size savings.
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=None,
)

# ── macOS .app bundle (only on macOS) ─────────────────────────────────
if IS_MACOS:
    app = BUNDLE(
        exe,
        name="OWNE Backend",
        icon=None,
        bundle_identifier="ai.orion.ownex.backend",
        info_plist={
            "LSUIElement": True,  # No dock icon
            "LSBackgroundOnly": True,
        },
    )
