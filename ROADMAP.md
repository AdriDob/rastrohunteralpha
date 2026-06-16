# ROADMAP — RASTRO INVESTIGATION OS
**Versión:** 1.3.0
**Fecha:** Junio 2026
**Visión:** Sistema Operativo Privado de Investigación para analistas de bug bounty y attack surface intelligence.

## 1. Estado Actual Real del Sistema

Rastro — **estable con pipeline integrado, Android scaffold, sidebar unificada**:

- **Backend**: FastAPI + SQLAlchemy + SQLite/PostgreSQL, 236 rutas, 38 routers, auth + rate-limit + license middleware.
- **Base de datos**: 17 tablas (SQLite default, PostgreSQL via DATABASE_URL).
- **Pipeline Unificado**: Target → Recon → Hypotheses → Validation → Evidence → Findings → Reports → Investigation con timeline y progreso visual.
- **Discovery Engine**: Subfinder, Katana, Httpx vía Go binaries con scheduler async (30min).
- **Frontend**: React 19 + Vite 8, build ~1.7s, 0 TS errors, 27 páginas, onboarding UX, sidebar con submenús.
- **Android**: Capacitor 8 scaffolded, APK build script, mobile bottom nav.
- **Personal Learning Engine**: 7 módulos backend + 12 endpoints + 19 tests + UI dedicada.
- **i18n**: Español default, auto-detect OS language, EN/ES completos, arquitectura para PT/FR/DE/IT.
- **User Auth**: Registro, login, refresh tokens, perfil — PBKDF2-HMAC-SHA256 (stdlib, sin bcrypt).
- **AI Layer**: Ollama (Qwen2.5-Coder) + OpenAI-compatible + fallback local rule-based + MemoryBuilder PLE.
- **Investigation Narrator**: 7 funciones de interpretación de inteligencia.
- **Test suite**: 152/152 passed (incluyendo 11 tests de seguridad + 11 auth + 19 PLE).
- **Auth**: JWT middleware global + User model + register/login/refresh/me.
- **Rate limiter**: Token bucket — 30/s default, login 5/s, overview 10/s.
- **License system**: HMAC-SHA256, machine fingerprint, persistencia, 3 endpoints + frontend Activation.
- **Onboarding UX**: WelcomeWizard + TourOverlay + BootScreen.
- **Auto-updater**: GitHub Releases + SHA-256 + rollback.
- **Windows lifecycle**: install/uninstall scripts, Add/Remove Programs, shortcuts.
- **Project Governance**: PROJECT_STATUS.md, TIMELINE.md, FEATURE_MATRIX.md, TECH_DEBT.md.
- **Hardening**: P1-P8 completado + Dual DB + migration script.
- **Housekeeping**: Legacy removals, 21 dead API functions eliminadas, dead components removidos.

## 2. Arquitectura Real Observada

```
Middleware: CORS → RateLimit → Auth (global)
Backend:    FastAPI modular con 37 routers + 183 rutas
DB:         SQLite (default) + PostgreSQL via DATABASE_URL (17 tablas)
Frontend:   React 19 + Vite 8 + Tailwind 4 + 25 páginas
Desktop:    pywebview 6 + pystray 0.19.5 + PyInstaller
Engine:     core_engines/ (recon, scoring, graph, evidence, verdict, report)
AI:         core_engines/ai/ (conversacional) + core_engines/assistant/ (narrativo)
Auth:       core_engines/auth/ + api/middleware/auth_middleware.py
License:    core_engines/license/ (validator, hardware, store)
```

## 3. UX Transformation Phase (Investigation OS) — COMPLETADO

**Pilares clave (completados):**
- Mission-First Dashboard: Quick Actions bar + auto-select target + misión del día.
- AI Copilot Contextual: Sugerencias por ruta activa.
- Command Palette (Ctrl+K): Shortcuts visibles, recent targets, badges por sección.
- Investigation Narrator: 7 endpoints de interpretación.
- Sidebar extraída: Colapsable, búsqueda, favoritos, 6 secciones.
- Onboarding: BootScreen + WelcomeWizard + TourOverlay.

## 4. Productization Hardening (P1-P8) — COMPLETADO

| ID | Área | Estado |
|----|------|--------|
| P1 | Auth middleware global | JWT en todas las rutas protegidas |
| P2 | Rate limiter | Token bucket con path-pattern rules |
| P3 | Security tests | 11 tests: auth + rate-limit |
| P4 | License system | HMAC + fingerprint + persistencia + frontend |
| P5 | Onboarding UX | WelcomeWizard + TourOverlay |
| P6 | Windows product lifecycle | install/uninstall + Add/Remove Programs |
| P7 | Auto-updater | GitHub Releases + SHA-256 + rollback |
| P8 | N+1 performance optimization | Score cache batch en overview/data_service |

## 5. Features Existentes (Verificadas)

- Motor de descubrimiento (subfinder, katana, httpx)
- Persistencia de endpoints y findings
- Sistema de scoring determinista con cache LRU
- Dashboard con 24 páginas y navegación completa
- AI Copilot + Briefing diario + Bounty potential
- Command Palette con shortcuts + búsqueda + badges
- Sidebar colapsable con favoritos y 6 secciones
- Onboarding: BootScreen + WelcomeWizard (3-step) + TourOverlay (3-step)
- License: Activation page + 403 interceptor
- 122 tests, build ~950ms, 0 TS errors
- 15 tablas (targets, endpoints, findings, verdicts, evidence, etc.)

## 6. Issues Conocidos (Baja Prioridad)

- `targets_intel` campos NULL — datos incompletos
- 3 `scan_runs` stuck en "running" — registros huérfanos
- StarletteDeprecationWarning por `httpx` (usar httpx2)
- `datetime.utcnow()` deprecado en `schemas.py`

## 7. Roadmap Futuro

### Short-term (v1.2.x)
- [x] Personal Learning Engine (PLE) — backend + frontend + tests
- [x] i18n — español default, auto-detect, arquitectura multi-idioma
- [x] Project governance — status, timeline, feature matrix, tech debt
- [x] User auth — registro, login, refresh, perfil
- [x] Dual DB — SQLite + PostgreSQL + migration script
- [ ] WebSocket manager + event bus bridge
- [ ] SSE fallback for restricted networks
- [ ] Client-side WebSocket hook

### Medium-term (v1.3.x)
- AI Provider abstraction layer (Ollama, OpenAI, OpenRouter, LM Studio, vLLM)
- Provider registry + auto-fallback chain
- Model selector UI
- SSE streaming endpoint
- Dashboard widgets (PLE-powered)
- Weekly progress charts
- Investigation heatmap

### Long-term (v2.0)
- PostgreSQL como DB principal (SQLite sigue siendo compatible)
- WebSocket + SSE sync layer
- Android app via Capacitor
- iOS app structure
- Notificaciones multiplataforma (FCM + Email + Desktop)
- Cuenta de usuario con sincronización cloud
- FREE / PRO / ELITE feature flags
- Sistema de permisos preparado para monetización

## 8. Riesgos de Evolución

- Sobrecarga cognitiva con demasiados widgets
- Dependencia excesiva de AI → pérdida de agency del usuario
- Complejidad del packaging multiplataforma
- Rendimiento con datasets grandes (>100k endpoints)
- Mantenimiento de compatibilidad backend-frontend
