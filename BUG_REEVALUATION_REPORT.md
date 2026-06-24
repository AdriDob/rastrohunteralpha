# BUG_REEVALUATION_REPORT.md

> Re-evaluación de bugs contra código consolidado en HEAD `81a5736`.
> Basado en BUG_ANALYSIS_COMPLETE.md como referencia histórica.

---

## Bug #1 — `open_dashboard()` got unexpected keyword argument 'onboarding'

**Estado:** ✅ RESUELTO
**Severidad:** Alta
**Archivo:** `desktop/browser_opener.py:77`, `frontend/src/App.tsx:174`
**Evidencia:**
- `build_dashboard_url()` acepta `onboarding: bool = False` (line 77)
- `open_dashboard()` acepta `onboarding: bool = False` (line 106)
- `App.tsx` lee `?onboarding=1` de URL (line 174)
**Conclusión:** Fix completo. Flujo: `_open_browser()` → `ctx["onboarding"]=True` → `build_dashboard_url(onboarding=True)` → `?onboarding=1` en URL → App.tsx procesa correctamente.

---

## Bug #2 (Error #2) — Loop infinito "Authenticating session"

**Estado:** ✅ RESUELTO
**Severidad:** Alta
**Archivo:** `frontend/src/lib/api.ts:44-50`, `frontend/src/stores/index.ts:68-74`, `frontend/src/App.tsx:83-90`
**Evidencia:**
- `api.ts` define `onAuthRedirect` callback que permite SPA navigation en 403
- `stores/index.ts` usa `getOverviewPreload()` con `__skipAuthRedirect: true` en rehidratación
- Catch block en `stores/index.ts:72-74` atrapa error sin rethrow → no hay crash
- `App.tsx:83-90` `AuthErrorHandler` configura `setOnAuthRedirect` con React Router `navigate`
**Conclusión:** Fix completo. No más loop: 403 no causa recarga de página, getOverviewPreload no redirige, catch previene crash.

---

## Bug #3 — GET /api/overview 401 Unauthorized

**Estado:** ✅ RESUELTO
**Severidad:** Alta
**Archivo:** `api/middleware/auth_middleware.py:36-37`, `desktop/main_desktop.py:221-254`, `desktop/browser_opener.py:82-83`
**Evidencia:**
- Auth middleware bypass para paths non-API (line 36-37)
- `_create_desktop_session()` crea sesión + token antes de abrir navegador
- Token pasado como `?token=` en URL (browser_opener.py:82-83)
**Conclusión:** Desktop session auto-auth funciona: sesión creada → token en URL → frontend lo extrae → API calls autenticadas.

---

## Bug #4 — ERR_CONNECTION_REFUSED

**Estado:** ✅ RESUELTO (para builds de release)
**Severidad:** Alta
**Archivo:** HEAD `40f34ba`, `desktop/settings.py:21`, `launcher/start.py:32`
**Evidencia:**
- Puerto 5173 → 8000 corregido en `40f34ba` para todos los archivos relevantes del release
- `launcher/start.py:32` mantiene `FRONTEND_PORT = 5173` pero SOLO afecta a `python launcher/start.py --dashboard react` (dev mode)
- `desktop/settings.py:21` `_LEGACY_PORTS = {5173}` es origen de migración, no puerto activo
- `launcher/start.py` no está empaquetado en PyInstaller (excluido en spec)
**Conclusión:** ERR_CONNECTION_REFUSED no ocurre en release builds. El 5173 residual está en scripts de desarrollo y legacy migration, no en el flujo de release.

---

## Bug #5 — Chunks JS fallando

**Estado:** ✅ RESUELTO
**Severidad:** Alta
**Archivo:** `api/middleware/auth_middleware.py:36-37`, `frontend/public/service-worker.js:75`
**Evidencia:**
- Non-API bypass permite que `/assets/*` pase sin auth
- Service Worker usa `networkFirst` (no `cacheFirst`) → no sirve respuestas 401/404 cacheadas
- `_mount_frontend()` sirve frontend estático
**Conclusión:** Chunks JS servidos correctamente. Service Worker prefiere red sobre cache.

---

## Bug #6 — MIME type application/json para archivos .js

**Estado:** ✅ RESUELTO
**Severidad:** Media
**Archivo:** `desktop/main_desktop.py:178-180`
**Evidencia:**
```python
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")
```
**Conclusión:** MIME types explícitamente registrados.

---

## Bug #7 (Error #7) — WebSocket cerrándose antes de completar conexión

**Estado:** ❌ PERSISTE
**Severidad:** Alta
**Archivo:** `api/routers/ws.py:14-42`
**Evidencia:**
- `websocket_endpoint()` verifica token pero NO llama a `is_license_valid()`
- Cuando licencia es inválida, WS conecta pero REST falla → comportamiento inconsistente
- `frontend/src/lib/ws.ts` token handling correcto (URL params → sessionStorage)
**Conclusión:** Falta agregar license check en WebSocket endpoint. Solución en 3 líneas.

---

## Bug #8 — Dashboard visible por instantes y luego caída

**Estado:** ⚠️ PARCIALMENTE RESUELTO
**Severidad:** Alta
**Archivo:** `frontend/src/lib/api.ts:44-50`, `frontend/src/stores/index.ts:50-82`, `frontend/src/components/BootScreen.tsx`
**Evidencia:**
- ✅ 403 usa SPA navigation (no recarga de página) — RESUELTO
- ❌ `onRehydrateStorage` no verifica licencia ANTES de mostrar dashboard — PERSISTE
- ❌ `BootScreen.tsx` no tiene estado de error UI — PERSISTE
**Conclusión:** La transición dashboard→activation es suave (SPA). Pero:
1. El dashboard se muestra aunque la licencia sea inválida
2. BootScreen nunca muestra error si algo falla

---

## Bug #9 — Diferencias entre run.py, uvicorn, build PyInstaller, EXE distribuido

**Estado:** ✅ RESUELTO
**Severidad:** Media
**Archivo:** `scripts/build_windows_exe.py:109`, `Rastro.spec:70`
**Evidencia:**
- `build_windows_exe.py:109` ahora usa `run.py` como entrypoint (corregido en FASE 3)
- `Rastro.spec:70` usa `['run.py']`
- SINGLE_SOURCE_OF_TRUTH.md documenta `run.py` como entrypoint oficial
- `uvicorn api.main:app` documentado como NO entrypoint válido para desktop
**Conclusión:** Entrypoint unificado. Fix aplicado, documentado y verificado.

---

## Bug #2 (de BUGS_ENCONTRADOS.md) — Asimetría auth WS/REST

**Estado:** ❌ PERSISTE (mismo bug que #7)
**Severidad:** Alta
**Archivo:** `api/routers/ws.py:14-42`
**Conclusión:** WS endpoint no verifica licencia. Corrección pendiente.

---

## Resumen de estado por bug

| # | Bug | Prioridad | Estado |
|---|---|---|---|
| 1 | `onboarding` kwarg crash | Alta | ✅ RESUELTO |
| 2 | Loop "Authenticating session" | Alta | ✅ RESUELTO |
| 3 | GET /api/overview 401 | Alta | ✅ RESUELTO |
| 4 | ERR_CONNECTION_REFUSED | Alta | ✅ RESUELTO |
| 5 | Chunks JS fallando | Alta | ✅ RESUELTO |
| 6 | MIME application/json | Media | ✅ RESUELTO |
| 7 | WS cerrándose temprano | Alta | ❌ PERSISTE |
| 8 | Dashboard→caída | Alta | ⚠️ PARCIAL |
| 9 | Diferencias entrypoints | Media | ✅ RESUELTO |
| B2 | Asimetría WS/REST auth | Alta | ❌ PERSISTE |

---

## Clasificación final

| Categoría | Cantidad | IDs |
|---|---|---|
| **CRÍTICOS ABIERTOS** | 0 | — |
| **ALTOS ABIERTOS** | 2 | #7 (WS sin license check), #8 (dashboard flash parcial) |
| **MEDIOS ABIERTOS** | 0 | — |
| **BAJOS ABIERTOS** | 0 | — |

---

## ¿Está listo para release?

**NO**

Razones:
1. **Bug #7 (Alta)**: WebSocket endpoint en `api/routers/ws.py:14-42` no verifica licencia. WS conecta sin licencia válida → comportamiento inconsistente.
2. **Bug #8 (Alta)**: Dashboard se muestra aunque licencia sea inválida. BootScreen sin estado de error. Aunque la transición a /activate es suave (SPA), el dashboard no debería renderizarse sin licencia válida.

### Lo que falta corregir antes del release

1. **Bug #7**: Añadir `is_license_valid()` check en `api/routers/ws.py` (3 líneas)
2. **Bug #8**: Verificar licencia en `onRehydrateStorage` ANTES de mostrar dashboard, y/o añadir estado de error en BootScreen
