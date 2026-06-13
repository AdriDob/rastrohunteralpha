# -*- mode: python ; coding: utf-8 -*-
#
# Rastro Desktop — legacy spec (kept for reference).
# Use Rastro.spec instead. This spec will be removed in a future release.

import os
from pathlib import Path

PROJECT_ROOT = Path(os.getcwd()).resolve()
FRONTEND_DIST = str(PROJECT_ROOT / "frontend" / "dist")

ROUTERS_DIR = PROJECT_ROOT / "api" / "routers"
router_modules = []
if ROUTERS_DIR.is_dir():
    for f in sorted(ROUTERS_DIR.iterdir()):
        if f.suffix == ".py" and f.stem != "__init__":
            router_modules.append(f"api.routers.{f.stem}")

CORE_DIR = PROJECT_ROOT / "core"
core_packages = []
if CORE_DIR.is_dir():
    for d in sorted(CORE_DIR.iterdir()):
        if d.is_dir() and (d / "__init__.py").exists() and d.stem != "__pycache__":
            core_packages.append(f"core.{d.stem}")

a = Analysis(
    ['run.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (FRONTEND_DIST, 'frontend_dist'),
    ],
    hiddenimports=[
        'desktop', 'desktop.main_desktop', 'desktop.settings',
        'desktop.autostart', 'desktop.browser_opener', 'desktop.notifications',
        'desktop.tray', 'desktop.serve_frontend', 'desktop.first_run',
        'api', 'api.main', *router_modules,
        'database', 'database.db', 'database.models',
        'core', 'core.config', 'core.env', 'core.env.config',
        'core.platform', 'core.platform.system',
        'core.log_config', 'core.observability',
        'core.intelligence', 'core.intelligence.adaptive_memory',
        *core_packages,
        'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
        'uvicorn.protocols', 'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets.auto',
        'httpx', 'sniffio', 'h11', 'anyio', 'pydantic',
        'pystray', 'PIL', 'PIL.Image', 'PIL.ImageDraw',
        'webview',
        'plyer', 'plyer.notification',
        'dotenv', 'sqlalchemy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    module_collection_mode={},
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='main_desktop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main_desktop',
)
