# BUG ANALYSIS COMPLETE — Verificación contra código actual

**Fecha:** 2026-06-24
**Propósito:** Para cada bug de los 9 errores observados por el usuario, determinar:
- Estado actual (reproducible o corregido)
- Causa raíz exacta (archivo:línea)
- Evidencia en código
- Corrección propuesta/verificada

---

## Error #1 — `open_dashboard() got an unexpected keyword argument 'onboarding'`

**Estado:** ✅ CORREGIDO (en working tree, sin commit)

**Causa raíz:** Commit `f7c5a8c` añadió `ctx["onboarding"] = True` en `_open_browser()` (`desktop/main_desktop.py:342-343`) pero `open_dashboard()` nunca fue actualizada para aceptar este parámetro. `**ctx` pasaba `onboarding=True` a `open_dashboard()` que no lo esperaba.

**Archivos afectados (original):**
- `desktop/browser_opener.py:70` — `build_dashboard_url()` sin parámetro `onboarding`
- `desktop/browser_opener.py:96` — `open_dashboard()` sin parámetro `onboarding`

**Archivos corregidos (working tree):**
- `desktop/browser_opener.py:77` — `onboarding: bool = False` añadido
- `desktop/browser_opener.py:90-91` — Appends `onboarding=1` a URL
- `desktop/browser_opener.py:106` — `onboarding` forwarding
- `frontend/src/App.tsx:171-177` — Lee `onboarding=1` de URL

**Evidencia en código actual:**
```python
# desktop/browser_opener.py:70-77
def build_dashboard_url(
    port: int = 8000,
    ...
    onboarding: bool = False,
) -> str:

# desktop/browser_opener.py:90-91
    if onboarding:
        params["onboarding"] = "1"
```

**Reproducción:** Con el código en HEAD (40f34ba), ejecutar `_open_browser(port)` que tiene `settings.get("onboarding_complete") is False` → añade `onboarding=True` al ctx → crash.

**Tests de regresión:** 4 tests en `test_desktop_release.py` verifican:
- `test_build_dashboard_url_with_onboarding`
- `test_open_dashboard_accepts_onboarding_kwarg`
- `test_open_browser_ctx_keys_are_valid_open_dashboard_params`
- `test_build_and_open_signatures_agree`

---

## Error #2 — Loop infinito "Authenticating session"

**Estado:** ⚠️ PARCIALMENTE CORREGIDO

**Causa raíz:** Múltiples causas encadenadas:

1. **`onRehydrateStorage`** en `frontend/src/stores/index.ts:50-82` se ejecuta como microtask ANTES de que React monte
2. Llama a `getOverview()` → `fetchJson('/overview')` 
3. Si licencia inválida → middleware devuelve 403
4. Originalmente: `window.location.href = '/activate'` → full page reload → loop
5. BootScreen muestra "Authenticating session" → página recarga → "Authenticating session" → ...

**Archivo:** `frontend/src/lib/api.ts:32-56`
**Función:** `fetchJson()`
**Línea original:** `window.location.href = '/activate'` (línea 35-37 original)

**Corrección aplicada (working tree):**
- `frontend/src/lib/api.ts:44-51` — 403 usa `onAuthRedirect()` si disponible (SPA navigation)
- `frontend/src/lib/api.ts:162-164` — `getOverviewPreload()` con `__skipAuthRedirect: true` para no redirigir en 403 durante rehidratación
- `frontend/src/stores/index.ts:69-70` — Llama `getOverviewPreload()` en vez de `getOverview()`
- `frontend/src/App.tsx:83-90` — Componente `AuthErrorHandler` configura `onAuthRedirect` vía React Router `navigate`

**Por qué sigue siendo parcial:**
- Si licencia es inválida, `getOverviewPreload()` falla silenciosamente (catch vacío en stores/index.ts:72-75)
- BootScreen se completa igual
- Dashboard se renderiza
- React Query llama `getOverview()` de nuevo → 403 → `onAuthRedirect('/activate')`
- Usuario ve dashboard por instantes, luego es redirigido a /activate

**Para corrección completa:**
- `frontend/src/stores/index.ts:72-75` — Añadir manejo visible de error
- `frontend/src/components/BootScreen.tsx` — Añadir estado de error (Bug #12)

---

## Error #3 — GET /api/overview 401 Unauthorized

**Estado:** ✅ CORREGIDO (en working tree, sin commit)

**Causa raíz:** `api/middleware/auth_middleware.py:37-44` — El middleware protegía TODAS las rutas, incluyendo `/api/overview`, pero el desktop nunca creaba un token de sesión.

**Árbol de causas:**
1. `AuthMiddleware.dispatch()` intercepta TODOS los requests
2. `/api/overview` no está en `PUBLIC_PATHS`
3. No hay header `Authorization: Bearer`
4. Retorna 401

**Corrección 1 — AuthMiddleware:** `api/middleware/auth_middleware.py:36-37`
```python
if not path.startswith("/api/"):
    return await call_next(request)
```
Esto permite que assets estáticos pasen sin auth.

**Corrección 2 — Desktop session:** `desktop/main_desktop.py:221-254`
```python
def _create_desktop_session(port: int) -> None:
    manager = get_auth_manager()
    result = manager.authenticate(device_id, {...})
    if result and "token" in result:
        settings.set_auth_tokens(session_token=result["token"], ...)
```
Crea sesión antes de abrir navegador (línea 482).

**Corrección 3 — Token en URL:** `desktop/browser_opener.py:82-83`
```python
params["token"] = token  # si token es truthy
```

**Evidencia de que funciona:** Lifecycle log muestra `[BOOT] Desktop session created (device=...)`

---

## Error #4 — ERR_CONNECTION_REFUSED

**Estado:** ✅ CORREGIDO (en HEAD commit 40f34ba)

**Causa raíz:** Puerto 5173 hardcodeado en 6 lugares del código RC1.

**Archivos:** Ver `ROOT_CAUSE_REPORT.md` sección 4.

**Corrección:** Commit `40f34ba` reemplaza todos los 5173 → 8000 o parámetro `port`.

**Evidencia:** Bytecode verificado — no contiene entero 5173.

**Riesgo residual:** `launcher/start.py:32` tiene `FRONTEND_PORT = 5173` pero NO está empaquetado en PyInstaller. Solo afecta a `python launcher/start.py --dashboard react`.

---

## Error #5 — Chunks JS fallando

**Estado:** ⚠️ PARCIALMENTE CORREGIDO

**Causa raíz 1 — Auth middleware:** `auth_middleware.py` sin fix retornaba 401 para `/assets/*` porque no estaban en PUBLIC_PATHS.

**Corrección 1:** `auth_middleware.py:36-37` — bypass para non-API paths ✅

**Causa raíz 2 — Service Worker:** `frontend/public/service-worker.js:74-77` original con `cacheFirst`. Si alguna vez se cacheó una respuesta 401/404 JSON, el SW la servía para siempre.

**Corrección 2:** `service-worker.js:75` — `networkFirst` ✅

**Causa raíz 3 — Backend sin frontend mount:** Si se ejecuta `uvicorn api.main:app` sin `_mount_frontend()`, no hay ruta para `/assets/*` → FastAPI devuelve 404 JSON.

**Corrección 3:** Documentación — usar `python run.py` no `uvicorn` directo. ⚠️ No hay protección automática.

**Evidencia CHUNK_AUDIT_REPORT.md:**
```
$ curl http://127.0.0.1:8095/assets/MissionControl-C-xcIiIE.js
→ 200 OK, Content-Type: text/javascript ✅

$ curl http://127.0.0.1:8081/assets/MissionControl-C-xcIiIE.js (sin frontend)
→ 404 Not Found, Content-Type: application/json ❌
```

---

## Error #6 — MIME type application/json para archivos .js

**Estado:** ✅ CORREGIDO (en working tree)

**Causa raíz:** `desktop/main_desktop.py:171-211` — `_mount_frontend()` no registraba MIME types. FastAPI/Starlette servía ciertos archivos con `application/json` por defecto.

**Corrección:** `desktop/main_desktop.py:178-180`
```python
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("image/svg+xml", ".svg")
```

**Archivo:** `desktop/main_desktop.py:171-180`
**Función:** `_mount_frontend(app)`

---

## Error #7 — WebSocket cerrándose antes de completar conexión

**Estado:** ⚠️ PARCIALMENTE CORREGIDO

**Causa raíz 1 — Token race condition:** WS intenta conectar ANTES de que `AppInitializer` guarde el token en sessionStorage.

**Archivo:** `frontend/src/lib/ws.ts:60-68,70-78`
**Función:** `getToken()`, `connect()`

**Flujo problemático:**
1. `main.tsx` renderiza `<App />`
2. `App` renderiza `<BootScreen />` (si bootComplete=false)
3. `<AppInitializer />` NO está montado (está dentro de BrowserRouter, que está DESPUÉS de BootScreen)
4. `WSBridge.tsx` probablemente llama `connect()` durante o después de boot
5. Token puede no estar disponible → WS conecta sin token o con token null

**Corrección 1:** `ws.ts:77` ahora busca token en URL params ANTES de sessionStorage. Si el token viene en URL (vía `build_dashboard_url`), se usa directamente.

**Causa raíz 2 — No license check en WS endpoint:** WS conecta pero las APIs REST fallan con 403 → usuario ve WS conectado pero app no funciona.

**Archivo:** `api/routers/ws.py:14-42`
**Estado:** NO CORREGIDO (Bug #2)

**Corrección propuesta:** Añadir `is_license_valid()` check en `websocket_endpoint()`:
```python
from core_engines.license import is_license_valid
valid, _ = is_license_valid()
if not valid:
    await websocket.close(code=4001, reason="License required")
    return
```

---

## Error #8 — Dashboard visible por instantes y luego caída

**Estado:** ⚠️ PARCIALMENTE CORREGIDO

**Causa raíz:** 
1. BootScreen completa (2.5s)
2. Session token está en URL → App.tsx lo extrae → navega a /
3. Dashboard se monta y renderiza
4. React Query en MissionControl llama `getOverview()`
5. 403 License required → `onAuthRedirect('/activate')`
6. Dashboard desaparece, Activation page aparece

**Archivos involucrados:**
- `api/middleware/auth_middleware.py:63-71` — License check
- `frontend/src/lib/api.ts:41-52` — 403 handler
- `frontend/src/pages/Activation.tsx` — Pantalla de activación

**Corrección aplicada:**
- `api.ts:44-51` — 403 ahora usa SPA navigation en vez de full page reload
- La transición dashboard→activation es suave (no hay flash de recarga)

**Lo que NO está resuelto:**
- El dashboard no debería mostrarse si la licencia no es válida
- Ideal: BootScreen verificaría licencia ANTES de permitir el acceso
- La solución actual es cosmética (SPA vs recarga)

**Corrección propuesta adicional:**
- `frontend/src/stores/index.ts` — `onRehydrateStorage` debería verificar licencia primero
- Si licencia inválida, redirigir a /activate inmediatamente sin mostrar dashboard

---

## Error #9 — Diferencias entre run.py, uvicorn, build PyInstaller, EXE distribuido

**Estado:** ⚠️ DOCUMENTADO, NO CORREGIDO

### Comparación detallada

| Aspecto | `run.py` | `uvicorn api.main:app` | PyInstaller (`Rastro.spec`) | EXE distribuido |
|---------|----------|----------------------|---------------------------|-----------------|
| Entrypoint | `main()` en `desktop/main_desktop` | FastAPI directamente | `run.py` como script | Binario compilado |
| Frontend mount | ✅ `_mount_frontend()` | ❌ NO | ✅ (hereda de run.py) | ✅ |
| Desktop session | ✅ `_create_desktop_session()` | ❌ NO | ✅ | ✅ |
| Lifecycle logging | ✅ | ❌ NO | ✅ | ✅ |
| Server thread | ✅ `ServerThread` | ❌ (main thread) | ✅ | ✅ |
| System tray | ✅ | ❌ | ✅ | ✅ |
| Auto-frontend build | ✅ `_ensure_frontend_build()` | ❌ | ❌ (frozen=True → return) | ❌ (frozen) |
| Browser/window | ✅ | ❌ | ✅ | ✅ |
| Señales (SIGINT) | ✅ | ❌ (uvicorn maneja) | ✅ | ✅ |

### Diferencias entre build scripts

| Script | Entrypoint | Frontend dist | Estado |
|--------|-----------|---------------|--------|
| `Rastro.spec` (PyInstaller oficial) | `run.py` | `frontend_dist` (datas) | ✅ Correcto |
| `build_windows_v15.ps1` | `run.py` via `Rastro.spec` | Ya construido | ✅ Correcto |
| `scripts/build_windows_exe.py` (old) | `desktop/main_desktop.py` DIRECTO | `frontend\\dist;frontend_dist` | ❌ **BYPASSEA run.py** — no llama `_ensure_frontend_build()` |

**⚠️ Hallazgo crítico:** `scripts/build_windows_exe.py:109` usa `desktop/main_desktop.py` como entrypoint DIRECTAMENTE, no `run.py`. Esto significa que el viejo script de build podría producir un EXE que no tiene `_ensure_frontend_build()`. Sin embargo, este script requiere Windows Python (WSL interop) y probablemente no se usó para la build final.

**El script correcto es `build_windows_v15.ps1`.**

### Recomendación
1. Eliminar `scripts/build_windows_exe.py` (obsoleto, entrypoint incorrecto)
2. Mantener solo `scripts/build_windows_v15.ps1` 
3. Documentar que `uvicorn api.main:app` NO es un entrypoint válido para desktop

---

## Bug #2 (de BUGS_ENCONTRADOS.md) — Asimetría auth WS/REST

Ya cubierto en Error #7 arriba. Resumen:

**Archivo:** `api/routers/ws.py:14-42`
**Función:** `websocket_endpoint()`
**Línea faltante:** No hay llamado a `is_license_valid()`
**Corrección propuesta:**
```python
from core_engines.license import is_license_valid
# Añadir después de verify_token, línea ~26:
valid_license, _ = is_license_valid()
if not valid_license:
    await websocket.close(code=4001, reason="License required")
    return
```

---

## Resumen de estado por bug

| # | Error | Prioridad | Estado | Archivo clave |
|---|-------|-----------|--------|---------------|
| 1 | `onboarding` kwarg crash | Alta | ✅ Corregido | `browser_opener.py:77,106` |
| 2 | Loop "Authenticating session" | Alta | ⚠️ Parcial | `api.ts:44-51`, `stores/index.ts:69-70` |
| 3 | GET /api/overview 401 | Alta | ✅ Corregido | `auth_middleware.py:36-37`, `main_desktop.py:221-254` |
| 4 | ERR_CONNECTION_REFUSED | Alta | ✅ Corregido | Commit 40f34ba |
| 5 | Chunks JS fallando | Alta | ⚠️ Parcial | `auth_middleware.py:36-37`, `service-worker.js:75` |
| 6 | MIME application/json | Media | ✅ Corregido | `main_desktop.py:178-180` |
| 7 | WS cerrándose temprano | Alta | ⚠️ Parcial | `ws.py:14-42`, `ws.ts:60-68` |
| 8 | Dashboard→caída | Alta | ⚠️ Parcial | `auth_middleware.py:63-71` |
| 9 | Diferencias entrypoints | Media | ⚠️ Documentado | Múltiples |
