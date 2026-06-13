# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

PROJECT_ROOT = Path(os.getcwd())

FRONTEND_DIST = str(PROJECT_ROOT / "frontend" / "dist")

a = Analysis(
    ['desktop/main_desktop.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (FRONTEND_DIST, 'frontend_dist'),
    ],
    hiddenimports=[
        'desktop', 'desktop.launcher', 'desktop.service_manager',
        'desktop.settings', 'desktop.autostart', 'desktop.browser_opener',
        'desktop.notifications', 'desktop.tray', 'desktop.service_mode',
        'desktop.serve_frontend', 'desktop.first_run',
        'api', 'api.main',
        'core', 'core.config', 'core.env', 'core.env.config',
        'core.platform', 'core.platform.system',
        'core.log_config', 'core.observability',
        'core.intelligence', 'core.intelligence.adaptive_memory',
        'database', 'database.db', 'database.models',
        'uvicorn', 'uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto',
        'uvicorn.protocols', 'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets.auto',
        'httpx', 'sniffio', 'h11', 'anyio', 'pydantic',
        'pystray', 'PIL', 'PIL.Image', 'PIL.ImageDraw',
        'webview',
        'plyer', 'plyer.notification',
        'dotenv',
        'sqlalchemy',
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
