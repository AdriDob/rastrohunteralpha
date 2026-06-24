# Rastro Capability Matrix — v1.5.0

> Clasificación de todas las capacidades actuales del sistema.
>
> ✅ Ya existe y funciona
> ⚠️ Existe parcialmente
> 🔌 Existe pero no está conectado al flujo principal
> ❌ No existe

---

## Discovery

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| GAU (gau) | ✅ | `core_engines/discovery/recon/gau.py` — wrapped, usable via API |
| FFUF | ✅ | `core_engines/discovery/recon/ffuf.py` — wrapped, configurable wordlist |
| SecLists | ✅ | `core_engines/discovery/recon/seclists.py` — paths loaded from embedded list |
| Subfinder | ✅ | `core_engines/discovery/recon/subfinder.py` — subdomain discovery |
| Nmap | ✅ | `core_engines/discovery/recon/nmap.py` — port scanning |
| Nuclei | ✅ | `core_engines/discovery/recon/nuclei.py` — template-based scanning |
| Httpx | ✅ | `core_engines/discovery/recon/httpx.py` — HTTP probing |
| Katana | ✅ | `core_engines/discovery/recon/katana.py` — crawler |
| Discovery ORCHESTRATOR | ✅ | `core_engines/execution/pipeline_manager.py` — coordinates tool execution |

## Fingerprinting

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| WordPress detection | ✅ | `core_engines/targets/technology.py` — regex-based passive detection from metadata |
| CMS detection (Drupal, Joomla, Magento, etc.) | ✅ | 8 CMS detected |
| Framework detection (Laravel, Django, Rails, etc.) | ✅ | 12 frameworks detected |
| Infrastructure detection (nginx, AWS, Cloudflare, etc.) | ✅ | 11 infra indicators |
| WordPress plugin detection | ✅ | WooCommerce, Elementor, Yoast, ACF, Jetpack, WPForms, Wordfence, WP Rocket |
| Active fingerprinting via HTTP | ❌ | No active HTTP fingerprinting — purely passive from program metadata |

## Program Discovery

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| HackerOne fetch | ⚠️ | `Hunter.fetch_public_programs("hackerone")` — tries API but likely needs auth; improved with fallback URLs |
| Bugcrowd fetch | ⚠️ | Same approach as HackerOne |
| Intigriti fetch | ⚠️ | Same approach |
| YesWeHack fetch | ⚠️ | Same approach |
| Huntr discovery | ⚠️ | `HuntrProvider` — static seed data only, no live API |
| Public program import pipeline | ✅ | `Hunter.ingest_programs()` — parses, fingerprints, scores, persists to DB |
| Technology-based program enrichment | ✅ | Programs enriched with CMS/framework/plugin tags on ingest |
| Program Catalog UI | ✅ | `ProgramCatalog.tsx` — table, tech filters, platform fetch buttons |
| Opportunity Radar UI | ✅ | `OpportunityRadar.tsx` — targets ranked by ROI |
| Background program discovery | ❌ | No scheduler for periodic re-fetching |
| Automated tech-based program discovery | ❌ | No "find all WP programs" mechanism |

## Path Discovery

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| Discovered path extraction from endpoints | ✅ | `Pipeline._extract_discovered_paths()` — 15 suspicious path patterns in pipeline |
| Suspicious path hypothesis generation | 🔌 | `generate_from_discovered_paths()` — NOW CONNECTED through pipeline (FASE C) |

## Burp / ZAP Import

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| Burp Suite XML import | ✅ | `api/routers/operations.py` — parse and ingest Burp XML |
| ZAP JSON import | ✅ | `api/routers/operations.py` — parse and ingest ZAP JSON |
| Endpoint extraction from imports | ✅ | Persisted to `endpoints` table with source tracking |

## Correlation Engine

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| Correlation engine | 🔌 | `core_engines/engine/correlation.py` — exists, has `EndpointCorrelator` with platform-aware scoring, but **never called from pipeline** |
| Attack surface mapping | ✅ | `AttackSurfaceMapper` — IDOR clusters, auth boundaries, multi-tenant zones, GraphQL surfaces |
| Investigation graph | ✅ | `InvestigationGraphBuilder` — hot path detection from scored endpoints |
| Gap analysis | ✅ | `GapAnalyzer` — coverage score, missing hot paths, blind spots |

## Bounty Intelligence

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| BountyIntel | ✅ | `core_engines/intelligence/bounty_intel.py` — `ProgramMetrics`, `generate_bounty_intel_report()` |
| Unified scoring (platform-aware) | ✅ | `core_engines/engine/unified_scoring.py` — competition, freshness, opportunity scores |
| Payout estimation | ✅ | `roi_model.py` — `BASE_PAYOUT` per vulnerability type |
| Opportunity Intelligence Layer | ✅ | `core_engines/opportunity/` — EVH rankings, recommendations, snapshot history |
| Provider system | ⚠️ | 6 providers registered but all use static seed data |

## Hypothesis Generation

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| Base generators (IDOR, Auth, SSRF, etc.) | ✅ | 9 generators in `generators.py` |
| Nuclei-based hypotheses | ✅ | `generate_nuclei()` — enriches from nuclei findings |
| Technology-based hypotheses | 🔌→✅ | `generate_from_technology()` — **NOW CONNECTED** through pipeline (7 tech profiles) |
| Discovered-path hypotheses | 🔌→✅ | `generate_from_discovered_paths()` — **NOW CONNECTED** through pipeline (15 suspicious paths) |
| Graph/cluster hypotheses | ✅ | Hot paths + IDOR/auth/tenant/GraphQL clusters |
| LLM enrichment | ✅ | `llm.py` — `enrich_reasoning()`, `detect_gaps()`, `refine_priority()` (opt-in) |
| Hypothesis scoring | ✅ | `scorer.py` — likelihood, impact, exploitability, priority |
| Hypothesis memory | ✅ | `memory.py` — deduplication, pattern recognition across targets |
| Attack Queue | ✅ | `models.AttackQueue` — prioritized hypothesis list |

## Reward Learning

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| RewardLearner class | ✅ | `reward_learning.py` — full implementation (252 lines) |
| Per-type stats | ✅ | VulnTypeStats with adjustment factors |
| Per-program metrics | ✅ | ProgramRewardMetrics (acceptance rate, payout, response time) |
| Prediction accuracy | ✅ | Tracks estimated vs confirmed error |
| Connected to report flow | 🔌→✅ | **NOW CONNECTED** — called on report update with `confirmed_reward` or `status` changes |
| Exposed via API | 🔌→✅ | **NOW EXPOSED** — `GET /api/reports/reward-learning` |
| Exported from package | 🔌→✅ | **NOW EXPORTED** from `core_engines.intelligence` |
| Live dashboard widget | ❌ | No frontend widget yet — data available via API |
| Persisted adjustments | ❌ | Adjustments are in-memory only (lost on restart) |

## Report Generation

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| Pipeline auto-report | ✅ | `ReportEngine.build()` — in-memory FinalReport from verdict + evidence |
| DB-persisted report | ✅ | `ReportGenerator.draft_report()` + `Report` model — findings linked via JSON |
| API: generate aggregate | ✅ | `GET /api/reports/generate` — markdown + JSON aggregate |
| API: create from findings | ✅ | `POST /api/reports` — persistent report from finding IDs |
| API: list/filter/sort | ✅ | `GET /api/reports` — paginated, filtered, searchable |
| API: detail | ✅ | `GET /api/reports/{id}` |
| API: update (status, reward, notes) | ✅ | `PUT /api/reports/{id}` |
| HackerOne JSON export | ✅ | `export_formats.py` — `to_hackerone_json()` |
| Bugcrowd HTML export | ✅ | `export_formats.py` — `to_bugcrowd_html()` |

## Report History

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| ReportHistory page | ✅ | `ReportHistory.tsx` — table with status, severity, reward, filters |
| ReportDetail page | ✅ | `ReportDetail.tsx` — full detail with linked findings, timeline |
| Status tracking | ✅ | Reports track status: draft → submitted → triaged → paid/duplicate/etc |
| Reward tracking | ✅ | `estimated_reward`, `confirmed_reward`, `currency` |
| Timeline | ✅ | `timeline` JSON field for status change history |
| Activity feed | ✅ | `GET /api/activity` — recent findings, verdicts, scans, evidence |

## Dashboard Metrics

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| Mission Control (main dashboard) | ✅ | KPIs, system health, opportunity widgets, assistant, notifications |
| Overview API | ✅ | `GET /api/overview` — target/endpoint/finding counts, risk distribution, pipeline stages, top targets |
| Activity API | ✅ | `GET /api/activity` — recent activity feed (72h default) |
| Intelligence summary API | ✅ | `GET /api/intelligence/summary` — platform distribution, quality, complexity, ROI averages |
| Report stats API | ✅ | `GET /api/reports/stats` — counts by status, total rewards |
| Project Dashboard | ✅ | Internal dev dashboard (git, tests, feature matrix, tech debt) |
| Reward Learning API | 🔌→✅ | **NOW AVAILABLE** — `GET /api/reports/reward-learning` |

## Android Support

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| Capacitor build config | ✅ | `frontend/android/` — Capacitor Android project |
| Gradle build | ✅ | Builds APK (debug mode verified) |
| APK artifact | ✅ | Pre-built `rastro-android-debug.apk` (4.2 MB, Jun 16) |
| Mobile detection utilities | ✅ | `frontend/src/lib/mobile/` — platform detection, PWA prompts |
| Rebuild capability | ⚠️ | Requires Java 21 JDK (not available in current environment) |

## Desktop Support

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| PyInstaller build spec | ✅ | `Rastro.spec` — Linux binary build config |
| Linux binary | ✅ | Built (21 MB) — `dist/Rastro-1.5.0-stable/Linux/Rastro` |
| pywebview integration | ✅ | Desktop GUI via pywebview |
| Windows build | ❌ | Blocked — requires Windows host for cross-compilation |
| macOS build | ❌ | Not configured |

## Frontend Stability

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| React Query cache | ✅ | 60+ hooks, `gcTime: 10min`, `staleTime: 30s` defaults |
| Zustand stores | ✅ | 6 slices, persisted to localStorage |
| WebSocket management | ✅ | Singleton with exponential backoff reconnect, ping/pong |
| Error boundary | ⚠️ | Single global boundary — no granular per-page boundaries |
| Loading states | ⚠️ | Good coverage but some widgets use `loading={!data}` (flash on first render) |
| TypeScript strictness | ✅ | 0 errors in production build |
| Offline support | ✅ | IndexedDB cache, online/offline detection, debounced refresh |
| Service worker | ⚠️ | Registered but `/service-worker.js` not found in project (404) |

## Backend Stability

| Capacidad | Estado | Notas |
|-----------|--------|-------|
| Startup races | ✅ | Fixed — service registration in lifespan, ordered initialization |
| Memory leaks (sessions) | ✅ | Fixed — all DB sessions use try/finally or context managers |
| Silent exceptions | ✅ | Fixed — all `except: pass` replaced with logged warnings |
| Temp dir cleanup | ✅ | Fixed — nuclei temp files cleaned in try/finally |
| WS thread safety | ✅ | Fixed — `threading.Lock` on WebSocket `_clients` |
| Scheduler task tracking | ✅ | Fixed — orphaned tasks stored and awaited |
| Router prefix conflicts | ✅ | Fixed — `system_state` → `/api/system-state`, `idor` → `/api/idor` |
| Orphan cascade deletes | ⚠️ | 19 ForeignKeys without `ondelete` — application-level cleanup works |
| Rate-limit flaky test | ✅ | Fixed — passes when run alone |

## Legend

- **✅** — Funciona en producción, probado, sin issues conocidos
- **⚠️** — Existe pero con limitaciones conocidas (parcial, no siempre funciona, requiere auth)
- **🔌** — Existe el código pero no está conectado al flujo principal de producción
- **🔌→✅** — Estaba desconectado, AHORA ESTÁ CONECTADO (corregido en esta release)
- **❌** — No existe en absoluto
