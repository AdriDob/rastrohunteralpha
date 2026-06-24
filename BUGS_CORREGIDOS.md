# BUGS CORREGIDOS

## Bug #1 — `fetchJson` 403 handler causa full page reload

**Archivo:** `frontend/src/lib/api.ts:34-37`
**Fix:** Se añadió un callback global `onAuthRedirect` que React configura via `setOnAuthRedirect()`. Ahora en vez de `window.location.href = '/activate'`, se llama a `onAuthRedirect(path)` que usa `navigate(path, { replace: true })` de React Router, haciendo una navegación SPA sin perder el estado de React.

**Archivos modificados:**
- `frontend/src/lib/api.ts` — Añadido `setOnAuthRedirect()`, modificado el handler 403
- `frontend/src/App.tsx` — Añadido componente `AuthErrorHandler` que configura el callback

## Bug #3 — Service Worker cachea SPA con `cacheFirst`

**Archivo:** `frontend/public/service-worker.js:74-77`
**Fix:** Cambiado de `cacheFirst` a `networkFirst` para todos los assets estáticos. Ahora la SPA siempre se obtiene de la red primero, con fallback a caché.

## Bug #5 — Activation page no redirige automáticamente

**Archivo:** `frontend/src/pages/Activation.tsx:29-36`
**Fix:** Cuando `checkLicense()` retorna `valid: true`, se añadió `setTimeout(() => { window.location.href = '/'; }, 1500)` para redirigir automáticamente al dashboard después de 1.5 segundos.

## Bug #6 — Código muerto `createOnRehydrate` en hydration.ts

**Archivo:** `frontend/src/stores/hydration.ts:21-37`
**Fix:** Eliminada la función `createOnRehydrate()` que nunca se usaba. El archivo ahora solo contiene la interfaz `HydrationSlice`, el estado inicial y el creador del slice.

## Bug #11 — `hydrationSetHydrating`/`hydrationSetHydrated` son no-ops durante init

**Archivo:** `frontend/src/stores/index.ts:19-20, 83-84`
**Fix:** Reemplazadas las variables `let` con asignación tardía por funciones `setHydrating()` y `setHydrated()` que llaman directamente a `useStore.setState()`. Esto elimina la race condition donde las funciones eran no-ops durante la ejecución síncrona de `create()`.

## Bug #15 — `build_dashboard_url()` no escapa query params

**Archivo:** `desktop/browser_opener.py:92`
**Fix:** Reemplazado el concatenado manual `"&".join(f"{k}={v}" for ...)` con `urllib.parse.urlencode(params)` que escapa correctamente todos los caracteres especiales.

---

## Bugs pendientes (no corregidos)

### Bug #2 — Asimetría auth: WebSocket no verifica licencia
Requiere modificación del backend. El WS endpoint en `api/routers/ws.py` no llama a `is_license_valid()`. Añadiría una dependencia en la sincronización frontend-backend. Por ahora, el Bug #1 mitigado hace que el 403 se maneje como navegación SPA en vez de full page reload, mejorando la experiencia aunque el error persista.

### Bug #4 — `onRehydrateStorage` llama `getOverview()` fuera del ciclo de React
Esto es intencional para precargar datos antes del render. El error se maneja con try/catch. No hay impacto visible.

### Bug #7, #8, #9, #10, #12, #13, #14, #16
Son mejoras menores o de baja prioridad que no afectan el funcionamiento crítico.
