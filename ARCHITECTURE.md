# Rastro — Arquitectura

## Descripción general

Rastro es un sistema de inteligencia de superficie de ataque y bug bounty semi-autónomo.
Arquitectura local-first con backend FastAPI, frontend React, y SQLite como almacenamiento.

## Principios

- **Señal sobre ruido**: heurísticas deterministas, etiquetas explícitas, scoring práctico.
- **Simplicidad**: módulos claros, sin dependencia pesada de ML en pipeline central.
- **Local-first**: todo corre en la máquina del usuario.
- **Bajo demanda**: nada corre en background sin intervención del usuario (excepto scan scheduler + notification poller).

## Middleware Chain

```
Request → CORSMiddleware → RateLimitMiddleware → AuthMiddleware → Router
```

1. **CORSMiddleware**: development (`*`), production (`http://127.0.0.1:8000`, `http://localhost:8000`, `app://`)
2. **RateLimitMiddleware**: Token bucket, 30/s burst 50 default. Excluye health/version/docs. Login: 5/s burst 10. Overview/Digest: 10/s burst 20. Retorna 429 + `X-RateLimit-Remaining`.
3. **AuthMiddleware**: JWT validation en todas las rutas excepto `PUBLIC_PATHS` (health, version, docs) y `PUBLIC_PREFIXES` (`/api/auth`, `/api/license`). También valida licencia (403 si no hay licencia válida).

## Flujo de ejecución real (verificado en runtime)

```
  Usuario
    │
    ▼
  Brave/Chrome → localhost:8000 (API) / localhost:5173 (Frontend dev)
    │                      │
    ▼                      ▼
  CORSMiddleware ──→ RateLimitMiddleware ──→ AuthMiddleware
    │
    ▼
  FastAPI (api.main) — 37 routers montados en /api/*
    │
    ├── Startup (25 pasos): init_db, event_bus, system_state, identity,
    │   orchestrator, execution_tracker, scorecard, memory,
    │   scan_scheduler, notification_poller, opportunity discovery
    │
    ├── CORS + Exception handler global
    │
    ▼
  SQLite (database/rastro.db)
    │
    ▼
  Respuesta JSON → Frontend React (Vite)
```

## Componentes backend

### `api/main.py` — Aplicación principal (usada por desktop)
- 37 routers montados desde `api/routers/`
- Endpoints adicionales: `/api/health`, `/api/version`, `/api/stats`, `/api/metrics`
- Importada por `desktop/main_desktop.py`
- **183 rutas totales** (179 router routes + 4 app-level)

### `api/middleware/`
- `auth_middleware.py` — AuthMiddleware: JWT + license check
- `rate_limit_middleware.py` — RateLimitMiddleware: token bucket

### `core_engines/assistant/` — Investigation Narrator
- `ai_assistant.py`: `InvestigationNarrator` — 7 funciones de interpretación
  - `explain_investigation_state()`, `generate_report_narrative()`
  - `explain_attack_path()`, `unified_reasoning()`
  - `explain_bounty_potential()`, `generate_daily_briefing()`
  - `generate_system_intelligence_report()`

### `core_engines/ai/` — AI Conversacional
- `assistant.py`, `advisor.py`, `analyzer.py`
- `context_builder.py`, `insights.py`, `memory.py`
- `provider.py` — Ollama, OpenAI, fallback local
- `recommendations.py`, `summary.py`

### `core_engines/engine/`
- `unified_scoring.py` — score() y score_target(), motor determinista con cache LRU
- `unified_classifier.py` — classify(), clasificación de endpoints

### `core_engines/validation/`
- `loop_engine.py`, `evidence_builder.py`, `verdict_handler.py`
- `replayer.py`, `confidence.py`, `rules.py`, `hardening.py`, `gate.py`

### `core_engines/evidence/`
- `graph.py` — `EvidenceGraph`
- `store.py` — `EvidenceStore`

### `core_engines/analysis/`
- `investigation_graph.py` — `InvestigationGraphBuilder` + `HotPathDetector` + `ClusterEngine`
- `analyzer.py` — `EndpointAnalyzer`
- `noise_reduction.py` — `NoiseReductionEngine`

### `core_engines/opportunity/`
- `engine.py`, `providers.py`, `scoring.py`, `scoring2.py`, `history.py`, `recommendations.py`

### `core_engines/reporting/`
- `report_engine.py`, `reporting.py`, `severity.py`, `export_formats.py`

### `core_engines/orchestrator/`
- `scan_service.py`, `assistant_orchestrator.py`, `pipeline.py`

### `core_engines/recon/`
- `runner.py`, `subfinder_runner.py`, `wayback_runner.py`, `httpx_runner.py`, `katana_runner.py`, `parser.py`

### Otros módulos core_engines
- `intelligence/` — `PriorityEngine`, `DependencyGraph`, `UnifiedOrchestrator`, `LearningLoop`, `TrendDetector`
- `memory/` — `MemoryStore`, `DecisionMemory`, `InsightArchive`, `IdentityGraph`, `PatternExtractor`
- `accountability/` — `OutcomeTracker`, `SystemScorecard`
- `explainability/` — `ExplanationEngine`, `DecisionTrace`
- `events/` — `EventBus`
- `auth/` — `AuthManager`, `SessionValidator`, `TokenService`
- `gateway/` — `RateLimiter`, `Version`, `Router`
- `license/` — `Validator`, `Hardware`, `Store`

## Base de datos

SQLite con SQLAlchemy. 15 tablas:

| Tabla | Propósito |
|-------|-----------|
| targets | Objetivos de bug bounty |
| endpoints | Endpoints descubiertos |
| findings | Hallazgos/vulnerabilidades |
| verdicts | Resultados de validación |
| evidence | Evidencia de validación |
| validation_results | Resultados detallados |
| scan_runs | Ejecuciones de scan |
| memory_records | Memoria del sistema |
| notifications | Notificaciones internas |
| favorites | Favoritos del workspace |
| tasks | Tareas operativas |
| sessions | Sesiones de trabajo |
| targets_intel | Inteligencia de objetivos |
| target_scopes | Scopes de objetivos |
| quick_wins | Quick wins identificados |

## Frontend

- React 19 + TypeScript 6 + Vite 8
- 24 páginas (22 lazy-loaded + Activation + NotFound)
- Componentes: CommandPalette, AssistantPanel, DesktopSidebar, BootScreen, WelcomeWizard, TourOverlay
- Store: Zustand con persistencia localStorage
- UI: Tailwind 4 + Radix UI + framer-motion + cmdk
- Data: TanStack Query + TanStack Table
- i18n: EN + ES
- Tema: detective_dark / aurora_light
- Compila a `frontend/dist/` (~950ms, 0 TS errors)

### Layout
- `Layout.tsx` — Sidebar + Outlet + AI Copilot
- `Sidebar.tsx` — 19 nav items, 6 secciones, colapsable, favoritos, búsqueda
- `CommandPalette.tsx` — Ctrl+K con ROUTE_MAP, mode tabs, recent targets, badges
- `AssistantPanel.tsx` — AI Copilot contextual

### Onboarding
- `BootScreen.tsx` — animación de carga inicial
- `WelcomeWizard.tsx` — 3-step first-run wizard
- `TourOverlay.tsx` — 3-step UI tour (Sidebar, Command Palette, Mission Control)
- `Activation.tsx` — license activation page

## Desktop (Windows 11 + Linux)

- `desktop/main_desktop.py` — entrypoint para PyInstaller
- Boot: 13 pasos (rollback check → settings → API import → frontend mount → uvicorn → health check → UI)
- UI modes: pywebview window (1400×900), system browser, o system tray (pystray)
- Auto-updater: GitHub Releases + SHA256 checksum + rollback on crash
- Build: PyInstaller via `Rastro.spec` → `dist/Rastro/Rastro.exe`
- Installer: `installer/install_windows.ps1` (LOCALAPPDATA + shortcuts + Add/Remove Programs)
- Uninstaller: `installer/uninstall_windows.ps1` (files + registry + user data opcional)

## Discovery Engine

| Componente | Estado |
|-----------|--------|
| ReconRunner | Activo bajo demanda |
| subfinder | Disponible en sistema |
| httpx | Disponible en sistema |
| katana | Disponible en sistema |
| wayback (curl) | Disponible |
| Scheduler automático | 30min interval en startup |
| Notification poller | Activo en startup |
| Opportunity refresh | Auto-descubrimiento en startup |

## Patrones de Arquitectura

- **Singleton**: get_assistant(), get_narrator(), get_engine(), get_system_state(), get_event_bus(), get_rate_limiter()
- **Provider**: AIProvider (Ollama, OpenAI, LocalFallback), BaseProvider (oportunidades)
- **Dataclass-first**: Modelos de dominio como dataclasses, SQLAlchemy solo para persistencia
- **Manual DB sessions**: Cada handler crea/cierra su propia sesión (sin DI)
- **Read-only intelligence**: Opportunity, Assistant, Desktop NUNCA modifican pipeline data
- **Chain of Responsibility**: Replayer → Rules → Confidence → Gate → VerdictHandler

## Pipeline Core (NO MODIFICAR)

```
Recon → Scoring → Graph → Evidence → Verdict → Report

Recon:     subfinder → httpx → katana → wayback → parser → persist
Scoring:   unified_scoring.score() + unified_classifier.classify()
Graph:     investigation_graph.py → hot path detection + clustering
Evidence:  validation loop (replayer → rules → confidence → gate)
Verdict:   verdict_handler.py → status + confidence + validation_report
Report:    report_engine.py → severity + CVSS + export formats
```
