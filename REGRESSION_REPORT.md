# REGRESSION_REPORT.md

> Análisis de regresiones introducidas por los cambios de consolidación y fixes.
> HEAD: `81a5736`

---

## Areas analizadas

| Área | Archivos clave |
|---|---|
| Auth Middleware | `api/middleware/auth_middleware.py` |
| Desktop session | `desktop/main_desktop.py`, `auth_manager.py` |
| Stores (frontend) | `frontend/src/stores/*.ts` |
| Módulos nuevos | `api/routers/discovery.py`, `core_engines/engine/correlation.py` |
| WebSocket | `frontend/src/lib/ws.ts` |
| Frontend new pages | `ProgramCatalog.tsx`, `ReportDetail.tsx`, `ReportHistory.tsx` |
| CORS / Server | `api/main.py` |
| run.py ↔ main_desktop.py | `run.py`, `desktop/main_desktop.py` |
| Build scripts | `scripts/build_windows_exe.py`, `Rastro.spec` |

---

## Resultados

| Área | Estado | Hallazgo |
|---|---|---|
| Auth Middleware | ✅ Sin regresión | Non-API bypass es por diseño. CORS middleware correctamente ordenado antes de AuthMiddleware. |
| Desktop session | ✅ Sin regresión | `_create_desktop_session()` maneja todos los modos de fallo (device_id faltante, authenticate falla) con try-except. |
| Stores | ⚠️ WARNING | `frontend/src/stores/hydration.ts` es código muerto (no importado). `hydrating`/`hydrated` state seteado como propiedades no tipadas. No es regresión de runtime. |
| Módulos nuevos | ✅ Sin regresión | `discovery.py` correctamente importado y registrado en `api/main.py`. `correlation.py` es standalone. |
| WebSocket | ✅ Sin regresión | No hay race conditions (JS single-threaded). Handlers nulleados antes de close(). Reconexión con exponential backoff. |
| Frontend new pages | ✅ Sin regresión | Lazy-loaded con routing correcto (`/reports/history` antes de `/reports/:id`). |
| CORS / Server | ✅ Sin regresión | Starlette refleja Origin cuando `*`+credentials en dev mode. Desktop mode restringe a localhost. |
| run.py ↔ main_desktop.py | ✅ Sin regresión | Path handling consistente. `run.py` es single entrypoint. Env vars seteadas en orden correcto. |
| Build scripts | ✅ Sin regresión | `build_windows_exe.py` usa `run.py`. `Rastro.spec` usa `run.py`. |

---

## Resumen

**Regresiones encontradas:** 0
**Warnings:** 1 (hydration.ts dead code — no impacta runtime)

---

## Nota sobre `hydration.ts`

El archivo `frontend/src/stores/hydration.ts` define `HydrationSlice` y `createHydrationSlice` pero nunca es importado por `frontend/src/stores/index.ts` ni ningún otro archivo. La funcionalidad de hydratación se maneja directamente via `useStore.setState()` en `index.ts:20-24`. Esto es código inactivo.

No representa riesgo de release, pero debería limpiarse en futura refactorización.

---

## Conclusión

**No se detectaron regresiones.** Los cambios de consolidación y fixes no introdujeron nuevos bugs.

Los únicos bugs pendientes son los ya documentados en BUG_REEVALUATION_REPORT.md (Bug #7 y #8 parcial), que existían antes de la consolidación.
