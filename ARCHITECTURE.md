# Rastro — Arquitectura

## Descripción general

Rastro es un sistema de inteligencia de superficie de ataque y bug bounty semi-autónomo.
Arquitectura local-first con backend FastAPI, frontend React, y SQLite como almacenamiento.

## Principios

- **Señal sobre ruido**: heurísticas deterministas, etiquetas explícitas, scoring práctico.
- **Simplicidad**: módulos claros, sin dependencia pesada de ML en pipeline central.
- **Local-first**: todo corre en la máquina del usuario.
- **Bajo demanda**: nada corre en background sin intervención del usuario.

## Flujo de ejecución real (verificado en runtime)

```
  Usuario
    │
    ▼
  Brave/Chrome → localhost:8000 (API) / localhost:5173 (Frontend dev)
    │
    ▼
  FastAPI (api.main)
    │
    ├── 35 routers montados en /api/*
    │   ├── targets, endpoints, findings → CRUD básico
    │   ├── opportunities, daily, overview → inteligencia
    │   ├── verdicts, evidence → validación
    │   ├── pipeline, attack-surface → análisis
    │   ├── scans → lanzar recon
    │   ├── assistant → AI conversacional + Investigation Narrator
    │   └── system, intelligence, operations → estado y operaciones
    │
    ├── Startup: init_db, event_bus, system_state, identity,
    │   orchestrator, execution_tracker, scorecard, memory,
    │   scan_scheduler, notification_poller
    │
    ├── CORS abierto (development)
    ├── Exception handler global
    │
    ▼
  SQLite (database/rastro.db)
    │
    ▼
  Respuesta JSON → Frontend React (Vite)
```

## Componentes backend

### `api/main.py` — Aplicación principal (usada por desktop)
- 35 routers montados desde `api/routers/`
- Endpoints adicionales: `/api/health`, `/api/version`, `/api/metrics`
- Importada por `desktop/main_desktop.py`
- **183 rutas totales** (176 originales + 7 narrator)

### `api/routers/assistant.py` (16 endpoints)
- `/api/assistant/context`, `/insights`, `/insights/top` — datos de contexto
- `/api/assistant/recommendations`, `/recommendations/best` — recomendaciones
- `/api/assistant/summary`, `/status`, `/history` — estado del assistant
- `/api/assistant/chat` — chat conversacional con AI
- `/api/assistant/investigation/{id}` — estado de investigación (NUEVO)
- `/api/assistant/narrative/{id}` — narrativa de reporte estilo HackerOne (NUEVO)
- `/api/assistant/attack-path/{id}` — razonamiento de ruta de ataque (NUEVO)
- `/api/assistant/unified/{id}` — razonamiento unificado Web2+Web3 (NUEVO)
- `/api/assistant/bounty/{id}` — potencial de bounty (NUEVO)
- `/api/assistant/briefing` — briefing diario del sistema (NUEVO)
- `/api/assistant/intelligence-report` — reporte de inteligencia completo (NUEVO)

### `core/assistant/` — Investigation Narrator (NUEVO)
- **`ai_assistant.py`**: `InvestigationNarrator` — capa de interpretación del sistema
  - `explain_investigation_state()` — interpreta graph + evidence + verdicts
  - `generate_report_narrative()` — narrativa de reporte HackerOne/Immunefi
  - `explain_attack_path()` — por qué existe un hotspot
  - `unified_reasoning()` — Web2 + Web3 en una sola narrativa
  - `explain_bounty_potential()` — payout potencial basado en señales reales
  - `generate_daily_briefing()` — briefing diario completo
  - `generate_system_intelligence_report()` — reporte de inteligencia del sistema

### `core/ai/` — AI Conversacional
- `assistant.py` — `ScanAssistant` (legacy) + `Assistant` (unified orchestrator)
- `advisor.py` — respuestas a consultas del usuario
- `analyzer.py` — `AIAnalyzer` (wrapper del unified_classifier)
- `context_builder.py` — construcción de contexto del sistema
- `insights.py` — generación de insights automáticos
- `memory.py` — memoria conversacional
- `provider.py` — abstracción de proveedores AI (Ollama, OpenAI, fallback local)
- `recommendations.py` — generación de recomendaciones
- `summary.py` — resúmenes diarios

### `core/engine/`
- `unified_scoring.py` — score() y score_target(), motor de scoring determinista
- `unified_classifier.py` — classify(), clasificación de endpoints

### `core/validation/`
- `loop_engine.py` — motor de validación
- `evidence_builder.py` — construcción de evidencia
- `verdict_handler.py` — manejo de veredictos
- `replayer.py` — replay de requests
- `confidence.py` — scoring de confianza
- `rules.py` — reglas de validación
- `hardening.py` — detección de WAF/rate limiting
- `gate.py` — admisión de reportes

### `core/evidence/`
- `graph.py` — `EvidenceGraph` (grafo en memoria de comparaciones + veredictos)
- `store.py` — `EvidenceStore` (CRUD para evidencia)

### `core/analysis/`
- `investigation_graph.py` — `InvestigationGraphBuilder` + `HotPathDetector` + `ClusterEngine`
- `analyzer.py` — `EndpointAnalyzer` (wrapper legacy)

### `core/opportunity/`
- `engine.py` — motor de oportunidades
- `providers.py` — proveedores de datos (PublicProgram, GitHub, Huntr, AllSources)
- `scoring.py`, `scoring2.py` — scoring de oportunidades v1 y v2

### `core/reporting/`
- `report_engine.py` — `ReportEngine`, `FinalReport`, `ProgramData`
- `reporting.py` — `ReportGenerator`
- `severity.py` — niveles de severidad, CVSS, confianza
- `export_formats.py` — formatos de exportación (HackerOne JSON, Markdown, Bugcrowd HTML)

### `core/orchestrator/`
- `scan_service.py` — lanza scans con ReconRunner
- `assistant_orchestrator.py` — orquestación de asistencias

### `core/recon/`
- `runner.py` — orquesta pipeline de recon
- `subfinder_runner.py`, `wayback_runner.py`, `httpx_runner.py`, `katana_runner.py`
- `parser.py` — normaliza endpoints

### Otros módulos core
- `core/intelligence/` — `PriorityEngine`, `DependencyGraph`, `UnifiedOrchestrator`
- `core/memory/` — `MemoryStore`, `DecisionMemory`, `InsightArchive`, `IdentityGraph`
- `core/accountability/` — `OutcomeTracker`, `SystemScorecard`
- `core/explainability/` — `ExplanationEngine`, `DecisionTrace`
- `core/events/` — `EventBus`
- `core/system_state.py` — `SystemState` singleton

## Base de datos

SQLite con SQLAlchemy. Tablas actuales:

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

## Frontend

- React + TypeScript con Vite 8
- 22 páginas con lazy loading + 1 catch-all 404
- Componentes: CommandPalette, AssistantPanel, DesktopSidebar
- Store: Zustand con persistencia localStorage
- Compila a `frontend/dist/`
- Servido por FastAPI en producción (desktop)
- Desarrollo: Vite dev server en puerto 5173

### Layout
- `Layout.tsx` — Sidebar (19 nav items, 6 secciones) + AI Copilot global (320px)
- `AssistantPanel.tsx` — Briefing diario, bounty potential, insights, recomendaciones
- `CommandPalette.tsx` — Ctrl+K overlay con ROUTE_MAP explícito, mode tabs, búsqueda

## Desktop (Windows 11)

- `desktop/main_desktop.py` — entrypoint para PyInstaller
- In-process: backend y frontend en un solo proceso
- System tray opcional
- Build: PyInstaller via `Rastro.spec`

## Discovery Engine

| Componente | Estado |
|-----------|--------|
| ReconRunner | Activo bajo demanda |
| subfinder | Disponible en sistema |
| httpx | Disponible en sistema |
| katana | Disponible en sistema |
| wayback (curl) | Disponible |
| Scheduler automático | Activo en startup |
| Notification poller | Activo en startup |
| Opportunity refresh | Activo bajo demanda |

## Patrones de Arquitectura

- **Singleton**: `get_assistant()`, `get_narrator()`, `get_engine()`, `get_system_state()`, `get_event_bus()`
- **Provider**: `AIProvider` (Ollama, OpenAI, LocalFallback), `BaseProvider` (oportunidades)
- **Dataclass-first**: Modelos de dominio como dataclasses, SQLAlchemy solo para persistencia
- **Manual DB sessions**: Cada handler crea/cierra su propia sesión (sin DI)
- **Read-only intelligence**: Opportunity y Assistant NUNCA modifican pipeline data
- **Chain of Responsibility**: Replayer → Rules → Confidence → Gate → VerdictHandler
