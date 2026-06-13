# -*- mode: python ; coding: utf-8 -*-
#
# Rastro Desktop — PyInstaller build spec.
# Single entrypoint: run.py → desktop/main_desktop.py → FastAPI + pywebview.
# Output: dist/Rastro/Rastro.exe  (or dist/Rastro/Rastro on Linux)
#
# Usage:
#   pyinstaller Rastro.spec -y          # one-dir build
#   pyinstaller Rastro.spec -y --onefile  # single .exe (Windows only)

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(os.getcwd()).resolve()
FRONTEND_DIST = str(PROJECT_ROOT / "frontend" / "dist")
ICON_PATH = str(PROJECT_ROOT / "desktop" / "build" / "icons" / "rastro.ico")

# ── Collect all router modules (automatically discovered) ──────────────
ROUTERS_DIR = PROJECT_ROOT / "api" / "routers"
router_modules = []
if ROUTERS_DIR.is_dir():
    for f in sorted(ROUTERS_DIR.iterdir()):
        if f.suffix == ".py" and f.stem != "__init__":
            router_modules.append(f"api.routers.{f.stem}")

# ── Collect all core_engines subpackages for hidden imports ──────────
CORE_DIR = PROJECT_ROOT / "core_engines"
core_packages = []
if CORE_DIR.is_dir():
    for d in sorted(CORE_DIR.iterdir()):
        if d.is_dir() and (d / "__init__.py").exists() and d.stem != "__pycache__":
            core_packages.append(f"core_engines.{d.stem}")

# ── Common hidden imports shared across platforms ────────────────────
BASE_HIDDEN = [
    # Desktop layer
    'desktop', 'desktop.main_desktop', 'desktop.settings',
    'desktop.autostart', 'desktop.browser_opener', 'desktop.notifications',
    'desktop.tray', 'desktop.serve_frontend', 'desktop.first_run',
    'desktop.updater',
    # API layer
    'api', 'api.main', *router_modules,
    # Database
    'database', 'database.db', 'database.models',
    # Core engines
    'core_engines', 'core_engines.config', 'core_engines.env', 'core_engines.env.config',
    'core_engines.platform', 'core_engines.platform.system',
    'core_engines.log_config', 'core_engines.observability',
    *core_packages,
    # Web server
    'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
    'uvicorn.protocols', 'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets.auto',
    # HTTP / networking
    'httpx', 'sniffio', 'h11', 'anyio',
    # Desktop UI
    'webview', 'pystray', 'PIL', 'PIL.Image', 'PIL.ImageDraw',
    'plyer', 'plyer.facades.notification', 'plyer.platforms.win.notification',
    # Config / serialization
    'dotenv', 'pydantic',
    # Database ORM
    'sqlalchemy',
]

a = Analysis(
    ['run.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (FRONTEND_DIST, 'frontend_dist'),
        (str(PROJECT_ROOT / "installer" / "uninstall_windows.ps1"), '.'),
        (str(PROJECT_ROOT / "VERSION"), '.'),
    ],
    hiddenimports=BASE_HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'notebook', 'jupyter'],
    noarchive=False,
    module_collection_mode={},
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Rastro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_PATH,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Rastro',
)
