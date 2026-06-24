# BUGS ENCONTRADOS

## CRÍTICOS

### Bug #1 — `fetchJson` 403 handler causa full page reload durante el boot

**Archivo:** `frontend/src/lib/api.ts:34-37`
**Impacto:** Si `getOverview()` (llamado desde `onRehydrateStorage`) recibe 403, `window.location.href = '/activate'` destruye todo el estado de React, causando un full page reload justo cuando el BootScreen está mostrando "Authenticating session". El usuario ve el texto un instante y luego la página se recarga.

**Reproducción:** Tener una licencia inválida/vencida y abrir la app de escritorio.
- El WebSocket se conecta (no verifica licencia)
- La API REST devuelve 403 (verifica licencia)
- `getOverview()` en `onRehydrateStorage` falla con 403
- 403 handler → `window.location.href = '/activate'` → full page reload
- El usuario ve "Authenticating session" → recarga → Activation page

**Fix propuesto:** Reemplazar `window.location.href` con navegación SPA vía React Router. Pero `fetchJson` está fuera del contexto React, así que se necesita un callback.

### Bug #2 — Asimetría auth: WebSocket no verifica licencia, REST sí

**Archivo:** `api/middleware/auth_middleware.py:63-71` vs `api/routers/ws.py:14-42`
**Impacto:** El WebSocket se conecta exitosamente sin licencia válida, dando la ilusión de que todo funciona. Pero las llamadas REST fallan con 403. Esto explica por qué el usuario ve WebSocket conectado pero la UI no avanza.

**Reproducción:** Licencia inválida. WS conecta, REST falla.

### Bug #3 — Service Worker cachea SPA con `cacheFirst` para `/`

**Archivo:** `frontend/public/service-worker.js:74-77`
**Impacto:** La SPA se cachea con estrategia `cacheFirst`. Si el SW no se actualiza, los usuarios reciben una versión antigua del frontend indefinidamente. Las correcciones del boot/auth flow nunca llegan.

**Reproducción:** 
1. Desplegar nueva versión del frontend
2. Abrir la app (SW sirve versión cacheada)
3. Los bugs persisten aunque el código nuevo esté desplegado

**Fix propuesto:** Cambiar a `networkFirst` para `/`, o forzar actualización del SW en cada build.

### Bug #4 — `onRehydrateStorage` llama `getOverview()` fuera del ciclo de React

**Archivo:** `frontend/src/stores/index.ts:64-67`
**Impacto:** `getOverview()` se llama desde el microtask de Zustand, ANTES de que React haya renderizado. Si falla con 401/403, el error se traga silenciosamente, pero la redirección (Bug #1) ya se disparó. Además, React Query hará OTRA llamada a `getOverview()` cuando MissionControl monte, duplicando requests.

**Reproducción:** Siempre. El `onRehydrateStorage` hace `getOverview()` en paralelo con el boot.

## ALTOS

### Bug #5 — `Activation.tsx` no redirige automáticamente cuando la licencia está activa

**Archivo:** `frontend/src/pages/Activation.tsx:29-36`
**Impacto:** Si el usuario llega a `/activate` con una licencia válida, ve "License Active" con un botón "Go to Dashboard" que debe clickear manualmente. No hay auto-redirección. Rompe el flujo de onboarding.

**Reproducción:** Tener licencia válida, abrir `http://127.0.0.1:8000/activate`. Ver pantalla de "License Active" sin redirección automática.

**Fix propuesto:** Redirigir automáticamente a `/` después de 1-2s si `activated === true`.

### Bug #6 — `createOnRehydrate` en `hydration.ts` está muerto

**Archivo:** `frontend/src/stores/hydration.ts:21-37`
**Impacto:** Código muerto. La función `createOnRehydrate` está definida pero NUNCA se usa. El `onRehydrateStorage` real está inline en `stores/index.ts:46-78`. Esto duplica la lógica de rehidratación y puede confundir a futuros desarrolladores.

**Reproducción:** Buscar referencias a `createOnRehydrate` — solo aparece en su definición.

### Bug #7 — No hay manejo de errores visible cuando getOverview falla en onRehydrateStorage

**Archivo:** `frontend/src/stores/index.ts:68-70`
**Impacto:** Si `getOverview()` falla, el error se traga en `catch {}`. No hay feedback visual. El usuario ve el BootScreen completarse y luego una app sin datos, sin saber que la API falló.

**Reproducción:** Desconectar el backend, abrir la app. BootScreen completa, pero dashboard muestra errores silenciosos.

### Bug #8 — `useEffect` en `AppInitializer` tiene dependencias vacías pero usa `searchParams`

**Archivo:** `frontend/src/App.tsx:88-111` (línea 110: `// eslint-disable-next-line react-hooks/exhaustive-deps`)
**Impacto:** Eslint desactivado para dependencias podría ocultar bugs de stale closures si `useSearchParams` cambia.

**Reproducción:** No reproducible actualmente, pero es una mala práctica.

## MEDIOS

### Bug #9 — Service Worker sin estrategia de actualización

**Archivo:** `frontend/public/service-worker.js`
**Impacto:** No hay lógica de `skipWaiting` en `install` (ya está), ni de `clients.claim()` en `activate` (ya está). Pero no hay versión dinámica ni migración. El caché se llama `rastro-static-v3` pero no hay mecanismo para incrementar la versión automáticamente.

**Reproducción:** No inmediato, pero con el tiempo el caché se vuelve obsoleto.

### Bug #10 — `main.tsx` usa StrictMode en desarrollo

**Archivo:** `frontend/src/main.tsx:15-17`
**Impacto:** StrictMode monta/desmonta/remonta componentes en desarrollo. BootScreen se reinicia desde fase 0 en el segundo mount. Añade ~400ms al tiempo de boot. No afecta producción pero dificulta debugging.

**Reproducción:** `npm run dev` → BootScreen tarda ~2.9s en vez de ~2.5s.

### Bug #11 — `hydrationSetHydrating`/`hydrationSetHydrated` son no-ops durante init

**Archivo:** `frontend/src/stores/index.ts:19-20, 83-84`
**Impacto:** Las funciones se asignan como no-ops en la declaración (línea 19-20) y luego se reasignan después de `create()` (línea 83-84). La llamada a `hydrationSetHydrating(true)` dentro del `onRehydrateStorage` (línea 50) se ejecuta SÍNCRONAMENTE durante `create()`, cuando la función todavía es no-op. El estado `hydrating` nunca se setea a `true`.

**Reproducción:** Siempre. Pero no hay componente que lea `hydrating`/`hydrated`, así que el impacto real es nulo.

### Bug #12 — BootScreen no tiene estado de error

**Archivo:** `frontend/src/components/BootScreen.tsx`
**Impacto:** Si ocurre un error durante el boot (API falla, token inválido), el BootScreen no lo muestra. Simplemente avanza los phases y llama `onComplete()`. El usuario ve la app con datos faltantes sin saber qué pasó.

**Reproducción:** Desconectar backend durante boot.

### Bug #13 — No hay validación de que el token del URL sea el mismo que el del sessionStorage

**Archivo:** `frontend/src/App.tsx:89-97` y `frontend/src/stores/index.ts:54-61`
**Impacto:** `onRehydrateStorage` y `AppInitializer` ambos leen el token del URL y llaman `setAuthToken()`. Si el URL cambia entre la ejecución de ambos (ej: navegación), podrían tener tokens diferentes. El último `setAuthToken` gana, pero no hay verificación.

**Reproducción:** Extremadamente raro. Requeriría que el navegador cambie la URL entre el microtask de Zustand y el effect de React.

## BAJOS

### Bug #14 — Service Worker registra en `load` event, puede perder mensajes

**Archivo:** `frontend/src/main.tsx:7`
**Impacto:** El SW se registra después del evento `load`. Si el SW necesita interceptar requests durante la carga inicial, podría perder algunos.

### Bug #15 — `build_dashboard_url()` no escapa valores en query params

**Archivo:** `desktop/browser_opener.py:69-95`
**Impacto:** Los valores de `token`, `device_id`, etc. se concatenan directamente al URL sin `urllib.parse.quote()`. Si el token contiene caracteres especiales (`&`, `=`, `#`), el URL se rompe.

**Reproducción:** Token con caracteres especiales (raro, pero posible con tokens HMAC en base64).

### Bug #16 — No hay validación de tipo en `saveSettings`/`loadSettings`

**Archivo:** `frontend/src/App.tsx:66-81`
**Impacto:** `JSON.parse(raw)` puede lanzar si el localStorage está corrupto. El `try/catch` lo maneja, pero silenciosamente usa defaults. El usuario pierde su configuración sin saberlo.

---

**Total: 16 bugs encontrados (4 críticos, 5 altos, 4 medios, 3 bajos)**
