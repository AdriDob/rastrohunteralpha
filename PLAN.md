# PLAN.md — Estado Real del Sistema Rastro

> **Idioma:** Español (CASTELLANO)
> **Última actualización:** 2026-06-13 (ciclo UX OS + BUILD FIX)
> **Regla:** Solo refleja estado VERIFICADO en código, runtime o DB

---

## 1. SNAPSHOT DEL SISTEMA

### Backend
- **FastAPI** — 183 rutas registradas, 36 routers montados
- **Database**: SQLite primaria en `database/rastro.db` (semilla: 5 targets, 50 endpoints, 8 findings, 54 verdicts, 834 memory_records)
- **Pipeline**: subfinder/katana/httpx vía Go binaries. Scheduler async vía lifespan.
- **Módulo**: `core/assistant/ai_assistant.py` — InvestigationNarrator con 7 funciones
- **Frontend**: React 19 + Vite 8. Build en ~0.9s. 22 páginas enrutadas.
- **Test suite**: 107/107 passed

### Estado General: ESTABLE — BUILD FIX + HOUSEKEEPING + UX OS MEJORADO

---

## 2. ROUTERS VERIFICADOS (36/36 montados en main.py)

Todos los routers en `api/routers/` están montados vía `app.include_router()`. Cero ROUTER_DESCONECTADO.

| Router | Prefix | Rutas | Estado |
|--------|--------|-------|--------|
| targets | `/api/targets` | 4 | ✅ |
| endpoints | `/api/endpoints` | 4 | ✅ |
| findings | `/api/findings` | 2 | ✅ |
| evidence | `/api/evidence` | 1 | ✅ |
| opportunities | `/api/opportunities` | 1 | ✅ |
| attack_surface | `/api/attack-surface` | 1 | ✅ |
| pipeline | `/api/pipeline` | 1 | ✅ |
| quick_wins | `/api/quick-wins` | 1 | ✅ |
| reports | `/api/reports` | 1 | ✅ |
| hypotheses | `/api/hypotheses` | 1 | ✅ |
| roi | `/api/roi` | 1 | ✅ |
| overview | `/api` | 4 | ✅ |
| assistant | `/api/assistant` | 16 | ✅ (+7 narrator endpoints) |
| scans | `/api/scans` | 3 | ✅ |
| digest | `/api/digest` | 1 | ✅ |
| verdicts | `/api/verdicts` | 3 | ✅ |
| attack | `/api/attack` | 1 | ✅ |
| validation | `/api/validation` | 1 | ✅ |
| differential_intelligence | `/api/differential-intelligence` | 3 | ✅ |
| canonical | `/api` | 14 | ✅ |
| intelligence | `/api/intelligence` | 8 | ✅ |
| system | `/api/system` | 6 | ✅ |
| screenshots | `/api/screenshots` | 1 | ✅ |
| operations | `/api/operations` | 19 | ✅ |
| opportunity_intelligence | `/api/opportunity` | 17 | ✅ |
| auth | `/api/auth` | 10 | ✅ |
| sync | `/api/sync` | 5 | ✅ |
| notifications | `/api/notifications` | 7 | ✅ |
| mobile | `/api/mobile` | 9 | ✅ |
| contracts | `/api/contracts` | 1 | ✅ |
| system_state | `/api/system` | 2 | ✅ |
| daily | `/api/daily` | 3 | ✅ |
| orchestrator | `/api/orchestrator` | 4 | ✅ |
| identity | `/api/identity` | 6 | ✅ |
| execution | `/api/execution` | 13 | ✅ |
| direct `@app` | `/api/health, /api/version, /api/stats, /api/metrics` | 4 | ✅ |

---

## 3. FRONTEND VERIFICADO

| Check | Estado |
|-------|--------|
| Build | ✅ ~0.9s, 137 módulos, 0 errores |
| Rutas en App.tsx | 22 explícitas + 1 catch-all |
| Archivos page/ | 22 archivos, 100% mapeados |
| Types vs API | 50+ tipos + 9 narrator, 0 faltantes |
| Imports rotos | 0 — todos resuelven |
| AssistantPanel | ✅ Context-aware (sugerencias por ruta) |
| CommandPalette | ✅ Shortcuts visibles + Recent Targets + badges |
| Sidebar | ✅ Extraído a componente propio (Layout.tsx -81%) |
| MissionControl | ✅ Quick Actions bar + auto-select target |

---

## 4. GAPS DETECTADOS (SOLO EVIDENCIA REAL)

| ID | Tipo | Archivo | Línea | Evidencia | Impacto | Prioridad |
|----|------|---------|-------|-----------|---------|-----------|
| GAP-001 | ~~IMPORT_ROTO~~ | CORREGIDO | — | Creado `core/ai/analyzer.py` con `AIAnalyzer` | Cerrado | ✅ |
| GAP-002 | ~~IMPORT_ROTO~~ | CORREGIDO | — | `core.validation.verdict_handler` | Cerrado | ✅ |
| GAP-003 | ~~THREAD_LEAK~~ | CORREGIDO | — | Thread movido a startup handler | Cerrado | ✅ |
| GAP-004 | ~~DB_DUPLICATE~~ | CORREGIDO | — | `rastro.db` raíz eliminado | Cerrado | ✅ |
| GAP-005 | ~~DB_STALE~~ | CORREGIDO | — | Archivo huérfano eliminado junto con GAP-004 | Cerrado | ✅ |
| GAP-006 | ~~DEPRECATED_API~~ | CORREGIDO | `api/main.py` | `@app.on_event("startup")` → lifespan | Cerrado | ✅ |
| GAP-007 | ~~DEPRECATED_CONFIG~~ | CORREGIDO | `core/gateway/schemas.py` | `class Config` → `model_config` | Cerrado | ✅ |
| GAP-008 | DB_INCONSISTENCY | `database/rastro.db` | — | `targets_intel` 5 filas con campos NULL | Datos incompletos | 🟢 BAJA |
| GAP-009 | DB_STALE_SCANS | `database/rastro.db` | — | 3 scan_runs stuck "running" | Registros huérfanos | 🟢 BAJA |

---

## 5. TASK QUEUE (COMPLETADA)

### ✅ TASK-001 → TASK-007 — Completadas en ciclos anteriores
### ✅ TASK-004 — DB duplicada eliminada
- `./rastro.db` eliminado. DB autoritativa: `database/rastro.db`

### ✅ TASK-005 — Migrado a lifespan
- `@app.on_event("startup")` reemplazado por `@asynccontextmanager lifespan`
- Sin deprecation warnings de FastAPI en startup

### ✅ TASK-006 — Pydantic model_config
- `class Config` → `model_config = ConfigDict(...)` en `core/gateway/schemas.py`
- Sin PydanticDeprecatedSince20 warnings

### ✅ TASK-008 — Fix build TypeScript
- `api.ts`: Conflicto `DailyBriefing` resuelto (import renombrado)
- `DailyMode.tsx`: Errores de tipos resueltos automáticamente
- Build: 0 errores TypeScript

### ✅ TASK-009 — Command Palette UX
- Shortcuts `g m`, `g d`, etc. visibles en nav items
- Recent targets desde store
- Badges de conteo por sección

### ✅ TASK-010 — Sidebar extraction
- `DesktopSidebar` y `MobileBottomBar` extraídos a `Sidebar.tsx`
- `Layout.tsx` reducido de 429 → 79 líneas (-81%)

### ✅ TASK-011 — AI Copilot contextual
- `currentPath` prop en AssistantPanel
- Sugerencias cambian según ruta actual (/target/, /evidence/, /insights/, etc.)
- Cero cambios en lógica AI

### ✅ TASK-012 — Dashboard polish
- Quick Actions bar (Run Scan, Hot Paths, Briefing, Opportunities, Reports)
- Auto-select target en store al cargar misión
- CTA prominente en MissionWidget

---

## 6. MÉTRICAS DE SALUD DEL SISTEMA

| Métrica | Valor |
|---------|-------|
| Endpoints 200 | 183/183 (100%) |
| Routers montados | 36/36 (100%) |
| DB seed data | 5 targets, 50 endpoints, 8 findings, 54 verdicts |
| Frontend build | ✅ 0.9s, 0 errores TS |
| Test suite | 107/107 passed |
| Deprecation warnings (nuestro código) | 0 |
| DB duplicadas | 0 |
| Módulos core/assistant | 1: `InvestigationNarrator` con 7 funciones |
| Layout.tsx tamaño | 79 líneas (era 429) |
| Sidebar | Componente propio (330 líneas) |
| CommandPalette | Shortcuts + recent targets + badges |

---

## 7. BLOQUEADORES

- Ningún bloqueo crítico. Sistema funcional y estable.
- Todos los gaps de prioridad alta/media están corregidos (GAP-001 → GAP-007).
- Gaps restantes (GAP-008, GAP-009) son cosmeticos/baja prioridad.

---

## 8. ESTADO UX / OS

El frontend está completo como Investigation OS:
- ✅ 22 rutas enrutadas con lazy loading
- ✅ MissionControl como landing con Quick Actions bar
- ✅ Sidebar con 19 items en 6 secciones (componente extraído)
- ✅ Command Palette con shortcuts + recent targets + badges
- ✅ AI Copilot contextual (sugerencias por ruta actual)
- ✅ Investigation Narrator layer (7 endpoints)
- ✅ Auto-select target en dashboard
- ❌ Widget drag & drop (pendiente)

---

## 9. DECISIONES TÉCNICAS

| Decisión | Fecha | Rationale |
|----------|-------|-----------|
| `core/assistant/` separado de `core/ai/` | 2026-06-12 | Separación de concerns |
| 7 endpoints narrator en router assistant | 2026-06-12 | Evita crear nuevo router |
| `getAssistantDailyBriefing` vs `getDailyBriefing` | 2026-06-12 | Evita colisión de nombres |
| Lifespan sobre `on_event` | 2026-06-13 | FastAPI recomienda lifespan; elimina deprecation warning |
| Sidebar extraído a componente propio | 2026-06-13 | Reducción de Layout.tsx -81%, testeable |
| AI Copilot contextual por ruta | 2026-06-13 | Zero cambios en AI, solo props + routing context |
