# Changelog

## v1.3.0 (2026-06-16)
- **Pipeline Integration**: Flujo unificado Mission Control → Investigation auto-creación → Pipeline/Hypothesis/Evidence/Reports scoped to investigation
- **Hypothesis → Investigation**: Botones "Promote to Investigation" funcionales, crean investigación con nombre generado desde hipótesis + target
- **Timeline + Progreso Visual**: Pipeline timeline con eventos por etapa, barra de progreso, indicador de confianza en InvestigationDetail
- **Cross-navigation**: Botones contextuales entre Investigation → Pipeline, Hypothesis, Evidence, Reports
- **Sidebar con submenús**: Navegación simplificada con submenús colapsables, sin pérdida de capacidades
- **Android Scaffold**: Capacitor Android inicializado, build script con Java 17+ check
- **Mobile Bottom Nav**: Actualizado con tabs foco mobile: Dashboard, Investigaciones, Evidencia, Reportes, Ajustes
- **Empty States**: Paginas principales con estados vacíos informativos y CTAs
- **Fix inconsistencias**: Raw fetch reemplazado por mutation hook, tipo Investigation duplicado eliminado
- **Stabilization**: 152 tests pasando, frontend build limpio, prebuild validation OK

## v1.2.0 (2026-06-13)
- **Personal Learning Engine** (PLE): 7 módulos backend + 12 endpoints REST + 19 tests + UI dedicada
- **Internationalization**: Español default, auto-detect OS language, EN/ES completos, 22 claves PLE
- **Project Governance**: PROJECT_STATUS.md, TIMELINE.md, FEATURE_MATRIX.md, TECH_DEBT.md
- **Project Dashboard**: 7 endpoints backend + frontend con 6 tabs, health score, progress rings
- **User Auth**: Registration, login, refresh tokens, profile (PBKDF2-HMAC-SHA256)
- **Dual DB**: SQLite default + PostgreSQL via DATABASE_URL + migration script
- **Consistency audit**: VERSION→1.2.0, APP_VERSION lee de VERSION file, docs stale archivados
- **Zero deprecation warnings**: `datetime.utcnow()` eliminado de schemas.py y export.py
- 152 tests passing, 0 TS errors, build ~1.4s

## v1.1.0 (2026-05)
- PyInstaller build para Windows + Linux
- AppImage build script
- NSIS installer para Windows
- Iconos oficiales en `installer/icons/`
- README premium rewrite con badges, demo flow, tree view
- UX Premium: framer-motion transitions, theme variable fixes
- 21 dead API functions eliminadas
- EVOLUTION_PLAN.md (10 semanas, 5 fases)

## v1.0.0 (2026-04)
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
