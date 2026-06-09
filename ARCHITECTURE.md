# Rastro Architecture

## Overview

Rastro is a lightweight bug bounty operating system designed to be practical, deterministic, and focused on high-signal recon for API and authorization testing. The architecture favors simple Python services, local-first data storage, and modular components that can be extended over time.

## Core Principles

- **Signal over noise**: prioritize deterministic heuristics, explicit labels, and practical scoring.
- **Simplicity over over-engineering**: use clear module boundaries and avoid heavy ML dependency in core pipeline.
- **Modularity**: each functional area is isolated in a dedicated package.
- **Local-first workflows**: tools run on the workstation with outputs stored under `targets/<target>/...`.

## Key Components

### `main.py`

The FastAPI backend defines the API surface and orchestrates core workflows:

- Target creation and listing
- Endpoint registration
- Findings persistence
- Recon scan execution via `ReconRunner`
- Endpoint analysis combining local heuristics and optional AI
- Daily digest of highest-risk endpoints

### `database/`

SQLite persistence with SQLAlchemy models:

- `Target`
- `Endpoint`
- `Finding`
- `MemoryRecord` (if memory features are used elsewhere)

### `core/recon/`

Recon workflow modules perform local tooling and parse outputs:

- `runner.py` — orchestrates the scan pipeline and output storage
- `subfinder_runner.py` — discovers subdomains
- `wayback_runner.py` — collects historical URLs
- `katana_runner.py` — crawls and fingerprints web targets
- `httpx_runner.py` — scans APIs and service endpoints
- `parser.py` — normalizes endpoints into structured, labeled data

### `core/analysis/`

Analysis utilities for endpoint and target metadata:

- `EndpointAnalyzer` — assigns labels and classifies endpoints
- `synthesize_target_meta` — summarizes endpoint patterns for scoring

### `core/scoring/`

Heuristic scoring weights for:

- endpoint risk
- target priority

Scores are deterministic and interpretable.

### `ai/`

AI integration is intentionally optional and local-first:

- `ollama_client.py` — wrapper for Ollama API calls
- `analysis.py` — high-level endpoint analysis orchestrator
- `prompts/` — prompt templates for concise, bug bounty-aware reasoning

### `core/attack/`

- `engine.py` — Attack Decision Engine that prioritizes actionable endpoint vectors, ownership risks, and manual test suggestions.

## Data Flow

1. User creates or registers a target via the API.
2. `ReconRunner.run_pipeline()` runs recon tools and writes outputs to `targets/<target>/recon`, `targets/<target>/analysis`, and `targets/<target>/endpoints`.
3. Endpoint parser normalizes discovered URLs and writes `normalized_endpoints.json`.
4. The backend scores endpoints and targets using heuristics and returns digest-ready summaries.
5. AI analysis is available as a secondary review layer, not as the primary scoring engine.

## Storage Layout

Targets are stored under `targets/<target_name>` with subfolders:

- `recon/` — raw tool outputs
- `endpoints/` — normalized endpoint artifacts
- `analysis/` — scanning summary and metadata
- `logs/`, `screenshots/` — auxiliary artifacts

## Workflow Example

- `POST /targets` to register a target
- `POST /scans` to run the recon pipeline
- `GET /digest` for high-priority endpoint signals
- `POST /analysis/endpoint` to inspect suspicious paths
- `POST /findings` to record issues

## Roadmap

Next practical improvements:

- persist normalized endpoint metadata into the database
- add endpoint deduplication by path pattern
- provide a Streamlit dashboard view for digest and endpoint risk
- add a lightweight `reports/` generator for high-priority findings

## Why this architecture

This design keeps the core pipeline deterministic and transparent, while leaving room for later upgrades:

- AI as an assistant, not the core engine
- local recon tooling + parser as the main discovery path
- simple REST API for integration with dashboards and scripts
- SQLite for lightweight persistence and quick iteration

## Auditoría: Estado actual del proyecto (resumen)

Este documento añade una auditoría del estado actual del repositorio, el flujo real de ejecución, y los pasos mínimos requeridos para convertir Rastro en un MVP operativo.

1) Estado por sistema

- Backend: FUNCIONAL en su mayor parte — `main.py` expone rutas centrales (`/targets`, `/scans`, `/digest`, `/analysis/endpoint`, `/findings`). Inicio con Uvicorn comprobado. PARCIAL: algunas rutas de gestión (jobs, report generator) son placeholders. NO IMPLEMENTADO: endpoints para gestionar Hunter/Targets Intelligence directamente.
- Dashboard: FUNCIONAL — `dashboard/app.py` renderiza 7 pestañas y la nueva pestaña `Targets Intelligence`. PARCIAL: integración end-to-end visual no totalmente verificada (necesita pruebas manuales en Streamlit).
- Recon: FUNCIONAL — `core/recon/runner.py` orquesta herramientas externas (subfinder, wayback, katana, httpx). PARCIAL: ejecución completa depende de disponibilidad de herramientas en el host y permisos; outputs parsers están implementados.
- Target Acquisition: FUNCIONAL BÁSICO — nuevo paquete `core/targets` con `hunter.py`, `parser.py`, `scorer.py`, `filters.py`, `models.py`. `Hunter.ingest_programs()` persiste programas y scopes. PARCIAL: `fetch_public_programs()` es conservador y puede no encontrar endpoints JSON públicos; no hay endpoint backend para arrancar ingest automatizado.
- Scoring: FUNCIONAL — heurísticas deterministas en `core/scoring` y `core/targets/scorer.py`. PARCIAL: pesos no validados con datos reales; tuning pendiente.
- AI Analysis: PARCIAL / OPCIONAL — wrapper mínimo para Ollama (`ai/analysis.py`) existe; falla con gracia si no disponible. No es crítico para scoring.
- Database: FUNCIONAL — SQLite con SQLAlchemy (`database/db.py`, modelos existentes). NUEVO: tablas `targets_intel`, `target_scopes` añadidas; `init_db()` crea tablas.
- Reporting: PLACEHOLDER — `reports/` previsto but no hay generador completo ni endpoints de export.
- Automation: PLACEHOLDER — no hay scheduler/cron integrado; APScheduler fue removido por diseño (aún se puede añadir si se desea).

Estimaciones rápidas:
- Completion general: ~80% de la funcionalidad base está implementada.
- Operational readiness: 60% — suficiente para pruebas locales y workflows manuales, requiere validación y hardening.
- Technical debt: MEDIO-ALTO — razones: falta de pruebas automatizadas, scoring sin validación, integración de herramientas externas no estandarizada.

2) Flujo de ejecución real (paso a paso)

1. El usuario crea un target vía `POST /targets` o desde la pestaña `Targets` en Streamlit.
2. El target se persiste en SQLite (`targets` table).
3. El usuario inicia un scan (`POST /scans` o botón "Run Scan" en dashboard). Backend llama a `ReconRunner.run_pipeline()`.
4. `ReconRunner` ejecuta herramientas locales (subfinder, wayback, katana, httpx según modo) y escribe artefactos en `targets/<name>/recon/` y `targets/<name>/analysis/`.
5. `core/recon/parser.py` / `core/recon/EndpointParser` normaliza endpoints y genera `normalized_endpoints.json`.
6. Normalized endpoints pueden guardarse en la tabla `endpoints` (flujo existente registra endpoints cuando se integran — revisar para confirmar persistencia automática en la base de datos en cada despliegue).
7. `core/scoring.Scorer` y `core/targets/scorer.py` calculan scores heurísticos para endpoints y targets.
8. `GET /digest` agrega y devuelve los endpoints de mayor riesgo (top N) con `risk_score`.
9. El dashboard consulta `/digest` para mostrar la pestaña `High Signal` y la pestaña `Targets Intelligence` lee `targets_intel` desde la DB para mostrar objetivos y acciones.
10. `AIAnalyzer` es llamado opcionalmente por `POST /analysis/endpoint` para enriquecer resúmenes (si Ollama está disponible).

3) Requisitos mínimos para MVP operacional

- Estabilidad del backend: asegurar que `POST /scans` maneje fallos y timeouts con claridad y registre logs.
- Recon reproducible: documentar y validar que las herramientas externas están instaladas y el runner maneja fallos parciales.
- Persistencia completa: escribir endpoints normalizados al modelo `Endpoint` en la DB y enlazar con `Target`.
- Digest determinista: `GET /digest` debe devolver consistentemente top-N con scores explicables.
- Dashboard básico: Streamlit con pestañas operativas, posibilidad de enviar a recon desde Targets Intelligence.
- Scoring estable: pesos por defecto documentados; ofrecer ajustes por config.
- Seguridad y saneamiento: validar entradas de usuarios, prevenir path traversal en `targets/<name>`.

Evitar para MVP: ML/entrenamiento, scraping contra términos de servicio, complejas pipelines asíncronas distribuidas.

4) Roadmap priorizado

PHASE 1 — Core operational MVP (estim. complejidad: baja-media)
- Tareas: persistir endpoints en DB; robustecer `POST /scans` con manejo de errores; pruebas end-to-end; hardening de inputs.
- Valor práctico: ALTO. Riesgo: MEDIO (herramientas externas).

PHASE 2 — Workflow refinement (estim. complejidad: media)
- Tareas: tuning de scoring; añadir filtros UI en Targets Intelligence; endpoint para ingestar programas públicos; job de refresco opcional.
- Valor práctico: MEDIO-ALTO. Riesgo: MEDIO.

PHASE 3 — Advanced automation (estim. complejidad: media-alta)
- Tareas: automatizar ingest programático (respetando TOS); notificaciones; pipelines asíncronas mejoradas; tests de integración.
- Valor práctico: MEDIO. Riesgo: MEDIO-ALTO.

PHASE 4 — Optional enhancements (estim. complejidad: variable)
- Tareas: reports generator, export a formatos (CSV/HTML), integraciones con trackers (Jira), safe AI assistants.
- Valor práctico: VARIABLE. Riesgo: BAJO-MEDIO.

5) Puntos débiles actuales

- Dependencia en herramientas externas: si `subfinder`/`katana`/`httpx` no están disponibles, el pipeline parcial falla.
- Hunter.fetch_public_programs() puede devolver lista vacía; requiere endpoints oficiales o scraping (evitar scraping).
- Scoring no validado con datos reales → riesgo de falsos positivos/negativos.
- Falta de tests automatizados y de CI.
- Dashboard necesita pruebas UX y rendimiento en sesiones con muchas entradas.
- Concurrency: `sqlite` con threads requiere `check_same_thread=False` (ya seteado) pero puede tener problemas con alto paralelismo.

6) Revisión de simplificación

- Mantener heurísticas deterministas (scoring) — buena relación costo/beneficio.
- Evitar integrar jobs/schedulers complejos por ahora; usar llamadas manuales o wrappers simples.
- Evitar ML salvo que haya dataset y objetivo claro.
- Consolidar parsers y scoring en interfaces limpias para pruebas unitarias.

7) Estimación de tiempo para MVP funcional

- Horas estimadas: 12–24h para estabilizar el core (persistencia endpoints, pruebas E2E, manejo de errores); 24–40h adicionales para tuning y refinamiento UI.
- Partes más difíciles: robustecer ejecución de herramientas externas y normalizar output heterogéneo; validar scoring con ejemplos reales.
- Lo que ya se puede probar: creación de target, ejecución de scans manuales locales (si herramientas instaladas), ingest y visualización de Targets Intelligence.
- Validar primero: persistencia de endpoints + `GET /digest` y flujo visual en Streamlit.

8) Documentación y próximos pasos

- He añadido esta auditoría al repo. Próximo paso recomendado:
	1. Ejecutar pruebas E2E locales: crear target → run scan → confirmar `normalized_endpoints.json` → confirmar `GET /digest`.
	2. Persistir endpoints en DB si no está activo.
	3. Ajustar scoring tras revisar 20–50 endpoints reales.

Si quieres, procedo ahora a:
- lanzar Streamlit y comprobar la pestaña `Targets Intelligence` visualmente (puedo ejecutarlo aquí), o
- añadir un endpoint backend para invocar `Hunter.fetch_public_programs()` de forma segura (solo si confirmas).

