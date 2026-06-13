# ROADMAP — RASTRO INVESTIGATION OS
**Versión:** 1.0.0
**Fecha:** Junio 2026
**Visión:** Sistema Operativo Privado de Investigación para analistas de bug bounty y attack surface intelligence.

## 1. Estado Actual Real del Sistema

Rastro — **producción-ready con hardening completo**:

- **Backend**: FastAPI + SQLAlchemy + SQLite, 183 rutas, 37 routers, auth + rate-limit + license middleware.
- **Base de datos**: SQLite única con seed data: 5 targets, 50 endpoints, 8 findings, 54 verdicts, 834 memory_records.
- **Discovery Engine**: Subfinder, Katana, Httpx vía Go binaries con scheduler async (30min).
- **Frontend**: React 19 + Vite 8, build ~950ms, 0 TS errors, 24 páginas, onboarding UX.
- **AI Layer**: Ollama (Qwen2.5-Coder) + OpenAI-compatible + fallback local rule-based.
- **Investigation Narrator**: 7 funciones de interpretación de inteligencia.
- **Test suite**: 122/122 passed (incluyendo 11 tests de seguridad).
- **Auth**: JWT middleware global — 401 en rutas protegidas, 403 si sin licencia.
- **Rate limiter**: Token bucket — 30/s default, login 5/s, overview 10/s.
- **License system**: HMAC-SHA256, machine fingerprint, persistencia, 3 endpoints + frontend Activation.
- **Onboarding UX**: WelcomeWizard + TourOverlay + BootScreen.
- **Auto-updater**: GitHub Releases + SHA-256 + rollback.
- **Windows lifecycle**: install/uninstall scripts, Add/Remove Programs, shortcuts.
- **Hardening**: P1-P8 completado (auth, rate-limit, tests, license, onboarding, updater, lifecycle, N+1 optimization).
- **Housekeeping**: Legacy removals (dashboard/, root main.py, main_desktop.spec, schema.sql, 3 dead components, differential/discovery skeletons).

## 2. Arquitectura Real Observada

```
Middleware: CORS → RateLimit → Auth (global)
Backend:    FastAPI modular con 37 routers + 183 rutas
DB:         SQLite (15 tablas, SQLAlchemy)
Frontend:   React 19 + Vite 8 + Tailwind 4 + 24 páginas
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

### Short-term
- UX Premium: design tokens, theme refinement, skeletal loading, transitions
- AI Provider abstraction layer + streaming SSE
- Engine polish: visual clustering, evidence traceability, human-language narrator
- Windows .exe via GitHub Actions CI

### Medium-term
- Widget system con drag & drop
- Modo offline mejorado
- Investigation Canvas (espacio infinito de hipótesis visuales)
- Replay Timeline Visual (evolución de target como película)

### Long-term
- AI Memory persistente entre sesiones
- Soporte para equipos (opcional)
- Integraciones externas (Burp, Nuclei, etc.)
- Versión nativa Windows + Linux estable

## 8. Riesgos de Evolución

- Sobrecarga cognitiva con demasiados widgets
- Dependencia excesiva de AI → pérdida de agency del usuario
- Complejidad del packaging multiplataforma
- Rendimiento con datasets grandes (>100k endpoints)
- Mantenimiento de compatibilidad backend-frontend
