# Rastro — Central System Plan v1.3.0
OPENCODE SIEMPRE LEES ESTO PRIMERO. SIEMPRE ACTUALIZA ESTE PLAN A LOS ÚLTIMOS CAMBIOS Y PRÓXIMAS ACTUALIZACIONES

---

Este documento es la **fuente de la verdad** del proyecto Rastro.
Refleja el código real, no aspiraciones. Cualquier discrepancia entre este plan y el código significa que el plan debe actualizarse.

---

## 1. Estado Real del Sistema

| Dimensión | Estado |
|-----------|--------|
| **Backend** | FastAPI + SQLAlchemy + SQLite — 236 rutas, 38 routers, 0 deprecation warnings |
| **Frontend** | React 19 + Vite 8 + TypeScript 6 — build ~2s, 0 errores TS |
| **Desktop** | pywebview 6 — native window + system tray + auto-updater |
| **Android** | Capacitor 8 — scaffolded, APK build requires Java 17/21 |
| **Auth** | JWT global middleware + rate limiter (token bucket) + license system (HMAC-SHA256) |
| **Tests** | 152/152 passing (11 test files) |
| **CI/CD** | GitHub Actions — `test.yml` (push) + `release.yml` (tag v*) |
| **DB** | SQLite, 17 tablas, 0 Alembic, schema via `create_all()` + ad-hoc ALTER TABLE |
| **Licencia** | HMAC-SHA256, hardware-bound, 5×5 base32, expiry-encoded |
| **AI** | Ollama (Qwen2.5-Coder) + OpenAI-compatible + fallback local rule-based + PLE MemoryBuilder |
| **Pipeline** | Flujo unificado: Target → Recon → Hypotheses → Validation → Evidence → Findings → Reports → Investigation con timeline y progreso |
| **Coherencia docs vs código** | ~95% (docs stale archivados, sincronización completa) |

---

## 2. Estructura del Repositorio

```
Rastro/
├── run.py                     ← Entrypoint único (dev/frozen/CI)
├── VERSION                    ← "1.0.0" — fuente única de verdad
├── Rastro.spec                ← PyInstaller build spec
├── requirements.txt           ← Python dependencies
│
├── api/
│   ├── main.py                ← FastAPI app factory
│   ├── middleware/
│   │   ├── auth_middleware.py       ← Auth + license enforcement
│   │   └── rate_limit_middleware.py ← Token bucket rate limiter
│   └── routers/               ← 37 routers, 179 rutas
│
├── core_engines/              ← 50+ entries (todo el negocio)
│   ├── engine/                ← Scoring + classification (unified_scoring.py)
│   ├── validation/            ← Loop, evidence, verdicts, confidence
│   ├── intelligence/          ← Priority engine, orchestrator, learning loop
│   ├── memory/                ← Store, decision memory, insight archive
│   ├── opportunity/           ← Engine + providers + scoring v1/v2
│   ├── ai/                    ← Conversational AI (Ollama, OpenAI)
│   ├── assistant/             ← Investigation Narrator
│   ├── auth/                  ← Auth subsystem (session, token, validator)
│   ├── gateway/               ← Rate limiter + schemas + versioning
│   ├── license/               ← Validator, hardware, store
│   ├── analysis/              ← Investigation graph + noise reduction
│   ├── evidence/              ← Graph + store
│   ├── reporting/             ← Report engine + CVSS + export formats
│   ├── recon/                 ← subfinder, httpx, katana, wayback
│   ├── actions/               ← Action engine + execution tracker
│   ├── accountability/        ← Outcome tracker + scorecard
│   ├── explainability/        ← Decision trace + explanation engine
│   ├── orchestrator/          ← Pipeline orchestration + scan service
│   ├── events/                ← Event bus
│   ├── learning/              ← Personal Learning Engine (7 módulos: profile, tracker, prioritizer, explainer, memory, export, router)
│   ├── identity/              ← Identity manager + device registry
│   ├── notifications/         ← Notification hub + push
│   ├── contracts/             ← DTO normalizers + validators
│   ├── targets/               ← TargetIntel + Scope models
│   ├── platform/              ← Platform detection
│   ├── web3/                  ← Web3 adapter
│   ├── clustering/            ← Clustering engine
│   ├── attack/                ← Attack decision engine
│   ├── differential_intelligence/ ← Differential analysis
│   ├── artifacts/             ← System-wide DTOs
│   ├── execution/             ← Differential engine + PoC generator
│   ├── screenshot/            ← Screenshot engine
│   ├── sync/                  ← Sync manager
│   ├── quick_wins/            ← Quick wins engine
│   └── system_state.py       ← System state singleton
│
├── frontend/
│   ├── dist/                  ← Production build
│   ├── src/
│   │   ├── pages/             ← 27 pages (25 lazy + Activation + NotFound + ProjectDashboard + PersonalIntelligence)
│   │   ├── components/        ← 24 componentes
│   │   ├── lib/               ← Store (Zustand), API client, i18n, theme, offline
│   │   └── types/index.ts     ← ~1500 lines TypeScript types
│   ├── vite.config.ts
│   ├── package.json           ← React 19, TanStack Query/Table, Zustand, Tailwind 4 + Capacitor
│   ├── capacitor.config.json  ← Android Capacitor config
│
├── desktop/
│   ├── main_desktop.py        ← Boot sequence, window management
│   ├── updater.py             ← GitHub Releases auto-update + rollback
│   ├── serve_frontend.py      ← Frontend static file server
│   ├── tray.py                ← System tray (pystray)
│   └── ... (6 modules más)
│
├── database/
│   ├── models.py              ← 17 ORM models (incl. User, InvestigatorProfile, LearningEvent)
│   ├── db.py                  ← Engine, session, init_db()
│   └── rastro.db              ← Live DB (seed data)
│
├── tests/                     ← 11 test files, 152 tests
│
├── installer/
│   ├── install_windows.ps1    ← Windows install (LOCALAPPDATA + shortcuts + registry)
│   └── uninstall_windows.ps1  ← Full removal
│
├── scripts/                   ← 20 scripts (build, release, seed, etc.)
│
└── .github/workflows/
    ├── test.yml               ← Push to main/dev + PR to main
    └── release.yml            ← Tag v* → build Windows + Linux + GitHub Release
```

---

## 3. Middleware Chain

```
Request → CORSMiddleware → RateLimitMiddleware → AuthMiddleware → Router
```

- **RateLimitMiddleware**: Token bucket, 30/s burst 50 default. Login: 5/s burst 10. Overview/Digest: 10/s burst 20.
- **AuthMiddleware**: `PUBLIC_PATHS` (health, version, docs) + `PUBLIC_PREFIXES` (`/api/auth`, `/api/license`). JWT + license check (403 si no license).

---

## 4. Startup Sequence (25 pasos)

1. `db.init_db()` — crea tablas + ALTER TABLE targets_intel
2. `get_event_bus()` — event bus singleton
3. `get_system_state()` — system state singleton
4-8. Registra servicios (backend, frontend, intelligence, assistant, discovery)
9. `state.report_healthy("backend")`
10. `bus.publish("system:boot:complete")`
11. `enforce_on_startup()` — product behavior rules
12. `get_identity_manager().ensure_identity()`
13. `get_orchestrator().suppress_noise_items(threshold=0.15)`
14-18. Inicializa execution_tracker, outcome_tracker, scorecard, explanation_engine, decision_trace
19-22. Inicializa memory_store, decision_memory, insight_archive, priority_engine
23. `get_engine().discover_all()` — oportunidades (non-fatal)
24. `ScanScheduler(interval=30min).start()` — background scans
25. `start_notification_poller()` — background notifications

---

## 5. Desktop Boot Sequence

1. Parse CLI args
2. `_setup_logging()`
3. Set env vars (`DATABASE_URL`, `RASTRO_BASE_DIR`, `RASTRO_DESKTOP=1`)
4. `_init_settings()` — DesktopSettings + first-run
5. `check_and_rollback_if_needed()` — restore from failed update
6. Schedule `mark_update_success()` after 15s grace
7. Import `api.main:app`
8. `_mount_frontend(api_app)` — sirve frontend/dist
9. Start uvicorn en background thread
10. `_wait_for_port()` + `_wait_for_health()`
11. Background thread: `check_for_updates()`
12. UI: pywebview window (1400×900) o navegador
13. Graceful shutdown

---

## 6. Backlog Real

### Sprint 1: Estabilización (COMPLETADO)
- [x] Fix `Rastro.spec`: hidden imports `plyer.platforms.win.notification` → eliminado
- [x] Icon/UPX conditional por OS en spec
- [x] CI workflow: cache-dependency-path agregado
- [x] Retag `v1.1.0-build2` para Windows .exe nativo

### Sprint 2: Documentación (COMPLETADO)
- [x] `OPENCODE_PLAN.md` reescrito con estado real del sistema
- [x] `ARCHITECTURE.md` actualizado (paths, router count, middleware, startup)
- [x] `ROADMAP.md` actualizado (test count, versión, P1-P8)

### Sprint 3: Cleanup (COMPLETADO)
- [x] Eliminar 3 dead React components: ExecutionPanel, SystemStatusBar, InstallBanner
- [x] Eliminar funciones de API no llamadas en `api.ts`
- [x] Eliminar legacy: dashboard/, main.py, schema.sql, etc.

### Sprint 4: UX Premium Foundation (PARTIAL — transitions + theme refinements done)
- [x] framer-motion transitions entre rutas
- [x] Theme detective_dark + aurora_light
- [ ] Design tokens en Tailwind config + CSS custom properties
- [ ] Skeleton loaders inteligentes
- [ ] Sidebar simplificada (19 → ~10 items)
- [ ] Empty states para todas las páginas

### Sprint 5: AI Provider Abstraction (PENDIENTE — v1.3.0)
- [ ] Interfaz unificada AIProvider
- [ ] Provider registry + auto-fallback chain
- [ ] Model selector UI
- [ ] SSE streaming endpoint

### Sprint 6: Engine Polish (PENDIENTE)
- [ ] Lenguaje más humano en Investigation Narrator
- [ ] Clustering visual en AttackSurface
- [ ] Trazabilidad visual en EvidenceCenter

### Sprint 7: Release (COMPLETADO)
- [x] Windows .exe desde GH Actions
- [x] ZIP distribution + LEAME.txt
- [x] NSIS installer build

### Sprint 8: PLE + i18n + Governance (COMPLETADO)
- [x] Personal Learning Engine (7 módulos backend + 12 endpoints + 19 tests + UI)
- [x] i18n upgrade (español default, auto-detect, 22 claves PLE)
- [x] Project Governance (4 documentos)
- [x] Project Dashboard (7 endpoints + frontend 6 tabs)
- [x] User auth (register/login/refresh/me, PBKDF2)
- [x] Dual DB (SQLite default + PostgreSQL + migration script)
- [x] Consistency audit (VERSION→1.2.0, APP_VERSION fix, docs stale archivados, deprecations fixed)

### Sprint 9: Pipeline Integration + Stabilization (COMPLETADO — v1.3.0)
- [x] Auto-creación de Investigation desde Mission Control (flujo unificado)
- [x] Pipeline scoped a Investigation (timeline, progreso, confianza)
- [x] Hypothesis → Investigation promotion funcional
- [x] Cross-navigation contextual (Investigation → Pipeline/Hypothesis/Evidence/Reports)
- [x] pipeline_state tracking + timeline visual + stage progress bars
- [x] Sidebar con submenús colapsables (secciones agrupadas)
- [x] Empty states para páginas principales
- [x] Fix raw fetch en InvestigationDetail → mutation hook
- [x] Fix tipo Investigation duplicado en types/index.ts
- [x] Android Capacitor scaffold + build script con Java 17+ check
- [x] Mobile bottom nav actualizado (Dashboard, Investigaciones, Evidencia, Reportes, Ajustes)
- [x] 152 tests pasando, frontend build limpio, prebuild OK

---

## 7. Pipeline Core (NO MODIFICAR)

```
Recon → Scoring → Graph → Evidence → Verdict → Report

Recon:     subfinder → httpx → katana → wayback → parser → persist
Scoring:   unified_scoring.score() + unified_classifier.classify()
Graph:     investigation_graph.py → hot path detection + clustering
Evidence:  validation loop (replayer → rules → confidence → gate)
Verdict:   verdict_handler.py → status + confidence + validation_report
Report:    report_engine.py → severity + CVSS + export formats
```

---

## 8. Reglas para Agentes IA

1. **NO** modificar pipeline core
2. **NO** cambiar DB schema
3. **NO** eliminar endpoints (183 actuales)
4. **NO** reescribir arquitectura base
5. **NO** inventar features inexistentes
6. **NO** duplicar sistemas existentes
7. **SIEMPRE** ejecutar tests después de cambios
8. **SIEMPRE** verificar build frontend después de cambios React
9. **Actualizar OPENCODE_PLAN.md** si hay discrepancia plan vs código
10. **VERSION file** es fuente única de verdad
11. **Prefiere stdlib** sobre nuevas dependencias
12. **Desktop modules** nunca modifican pipeline data

---

## 9. Comandos de Verificación

```bash
python -m pytest tests/ -q --tb=short       # 152 tests
cd frontend && npm run build                 # 0 TS errors, ~2s
python -c "from api.main import app; print('OK')"  # API imports
python scripts/prebuild.py                   # Validación completa
npx cap sync android                         # Sync Capacitor Android
```
