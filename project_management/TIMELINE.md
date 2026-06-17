# TIMELINE — Rastro

Línea temporal del proyecto desde su concepción hasta la versión actual.

---

## 🟢 v0.1 (Prototipo Inicial) — *2025 Q4*

**Estado:** ARCHIVED  
**Commit:** no tracking

- Primer prototipo funcional
- Pipeline básico: Recon → Scoring → Findings
- SQLite como almacenamiento
- CLI interface

---

## 🟢 v0.2 (UI Inicial) — *2026 Q1*

**Estado:** ARCHIVED  
**Commit:** no tracking

- Frontend React con interfaz básica
- FastAPI backend con rutas REST
- Sistema de targets y findings
- Evidence center

---

## 🟢 v1.0 (Core Stable) — *2026-04*

**Estado:** RELEASED  
**Tag:** `v1.0.0`

- 122 tests pasando
- 37 routers, 183 rutas
- Middleware chain completa (CORS → RateLimit → Auth)
- Sistema de licencias HMAC-SHA256
- Auto-updater vía GitHub Releases
- Desktop: pywebview + system tray + notificaciones
- Pipeline core: Recon → Scoring → Graph → Evidence → Verdict → Report
- 24 páginas frontend (22 lazy + Activation + NotFound)
- CI/CD con GitHub Actions

---

## 🟢 v1.1 (CI/CD + Release) — *2026-05*

**Estado:** RELEASED  
**Tags:** `v1.1.0`, `v1.1.0-build3`

- PyInstaller build para Windows + Linux
- AppImage build script
- NSIS installer para Windows
- Iconos oficiales en `installer/icons/`
- Path fixes: GOPATH env var, `get_data_dir()` en scan_service
- README premium rewrite con badges, demo flow, tree view
- UX Premium: framer-motion transitions, theme variable fixes
- 21 dead API functions eliminadas
- TargetSummary duplicate fix en types
- EVOLUTION_PLAN.md (10 semanas, 5 fases)

---

## 🟢 v1.2 (UX Premium + Foundation) — *2026-06*

**Estado:** IN PROGRESS  
**Commits:** `99ed2ac` +

### Completado
- **Dual DB**: SQLite + PostgreSQL via `DATABASE_URL`
- **Migration script**: `scripts/migrate_to_postgres.py`
- **User auth**: Modelo User, register/login/refresh/me, PBKDF2
- **Personal Learning Engine** (PLE):
  - InvestigatorProfile + LearningEvent (17 tablas)
  - EventTracker (8 tipos de eventos)
  - AdaptivePrioritizer (targets, findings, notifications)
  - Explainer (explicaciones humanas)
  - MemoryBuilder (contexto para AI)
  - ProfileExporter (JSON + Markdown)
  - Router REST (12 endpoints)
  - 19 tests PLE
  - Frontend: Personal Intelligence page
- **Internationalization**:
  - Español como idioma por defecto
  - Auto-detección de idioma del sistema operativo
  - 22 nuevas claves PLE traducidas
  - Arquitectura lista para PT/FR/DE/IT
- **Project Governance**:
  - PROJECT_STATUS.md
  - TIMELINE.md
  - FEATURE_MATRIX.md
  - TECH_DEBT.md

### Completado en v1.3.0
- WebSocket manager + event bus bridge + client hook + router
- Notification bridges registrados en startup (db, desktop, email, FCM, WS forwarder)

### Pendiente
- Phase 3: Notification system (desktop push + email + FCM configuraciones reales)

---

## 🔵 v1.3 (AI Providers) — *Planificado Q3 2026*

- Provider abstraction layer (Ollama, OpenAI, OpenRouter, LM Studio, vLLM)
- Model selector UI
- SSE streaming endpoint
- Provider auto-fallback chain
- Provider registry

---

## 🔵 v2.0 (Multi-Device) — *Planificado Q4 2026*

- PostgreSQL como DB principal (SQLite sigue siendo compatible)
- WebSocket + SSE sync layer
- Android app via Capacitor
- iOS app structure
- Notificaciones multiplataforma
- Cuenta de usuario con sincronización cloud
- FREE / PRO / ELITE feature flags

---

## 🏁 Hitos Clave

| Fecha | Hito | Versión |
|-------|------|---------|
| 2026-04 | Core pipeline completo | v1.0.0 |
| 2026-05 | CI/CD, builds, packaging | v1.1.0 |
| 2026-06 | UX Premium, PLE, i18n, governance | v1.2.0 |
| 2026-Q3 | AI Provider Layer, streaming | v1.3.0 |
| 2026-Q4 | Multi-device, sync, mobile | v2.0.0 |
