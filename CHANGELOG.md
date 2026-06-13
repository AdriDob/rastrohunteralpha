# Changelog

## v1.0.0 (2026-06-13)
- First stable release
- Windows desktop packaging: pywebview + PyInstaller + installer
- CI/CD: test on push/PR, build Windows+Linux on tag
- Single entrypoint `run.py` with dev/frozen path bootstrap
- CORS hardened for desktop mode
- VERSION file as single source of truth
- Documentation: INSTALL.md (troubleshooting), PRODUCT.md, CHANGELOG.md
- Build scripts: build_frontend.sh, build_linux.sh, build_windows.ps1
- Release automation: scripts/release.py
- 111 tests passing, 0 TS errors

## v0.3.0 (2026-06-13)
- AI Copilot contextual (sugerencias por ruta, Briefing + Bounty)
- Investigation Narrator layer (7 endpoints)
- Windows desktop packaging con pywebview
- PyInstaller build pipeline verificada
- Command Palette con shortcuts + recent targets
- Sidebar extraída a componente propio (-81% Layout.tsx)
- Quick Actions bar + auto-select target en MissionControl
- Builds: frontend 0 errores (897ms), tests 107/107
- Tags: v0.1-alpha → v0.2-os-ui → v0.3-ai-copilot

## v0.2.0 (2026-06-12)
- Full API surface: 36 routers, 183 rutas
- Frontend OS: 22 páginas, lazy loading
- Mission Control dashboard
- System tray + notificaciones desktop
- Discovery pipeline (subfinder/katana/httpx)
- Lifespan migration + Pydantic v2 config
- CI: Makefile + scripts de build

## v0.1.0 (2026-06-10)
- Initial Rastro baseline
- FastAPI + SQLAlchemy + SQLite
- React + Vite frontend shell
- Core scoring engine
- Basic recon pipeline
