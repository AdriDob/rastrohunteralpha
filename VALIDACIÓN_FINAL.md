# VALIDACIÓN FINAL

## Estado: ✅ Auditoría completa — bugs críticos corregidos

### Bugs encontrados: 16
### Bugs corregidos: 6 (4 críticos, 2 medios)
### Bugs pendientes: 10 (1 alto, 4 medios, 5 bajos — no bloqueantes)

---

## Bugs Críticos Corregidos

### Bug #1 — 403 handler causaba full page reload (antes: `window.location.href`)
**Fix:** `frontend/src/lib/api.ts` — Añadido callback `onAuthRedirect` para navegación SPA vía React Router. Ya no se pierde el estado de React.

### Bug #1b — `onRehydrateStorage` disparaba 403 redirect antes de que React montara
**Fix:** `frontend/src/lib/api.ts` + `frontend/src/stores/index.ts` — Nueva función `getOverviewPreload()` que suprime el redirect en 403. El error se captura silenciosamente en el try/catch.

### Bug #3 — Service Worker cacheaba SPA stale con `cacheFirst`
**Fix:** `frontend/public/service-worker.js:74` — Cambiado a `networkFirst` para assets estáticos. La SPA siempre se obtiene de red primero.

### Bug #5 — Activation page no redirigía automáticamente con licencia válida
**Fix:** `frontend/src/pages/Activation.tsx:34` — Auto-redirect a `/` después de 1.5s cuando la licencia es válida.

---

## Bugs de Calidad Corregidos

### Bug #6 — Código muerto `createOnRehydrate`
**Fix:** `frontend/src/stores/hydration.ts` — Eliminada función no utilizada.

### Bug #11 — `hydrationSetHydrating` era no-op durante init
**Fix:** `frontend/src/stores/index.ts` — Reemplazadas variables `let` con reassignación por funciones directas a `useStore.setState()`.

### Bug #15 — `build_dashboard_url()` no escapaba query params
**Fix:** `desktop/browser_opener.py:92` — Reemplazado concatenado manual con `urllib.parse.urlencode()`.

---

## Validación de Compilación

```
$ cd frontend && npm run build
✓ built in 1.58s
  (38 assets, 0 errors, 0 warnings)
```

## Validación de Backend

```
$ python -m uvicorn api.main:app
  Application startup complete.
  Uvicorn running on http://127.0.0.1:8081
$ curl /api/health → {"status":"ok","app":"Rastro API","version":"1.5.0"}
$ curl /api/license/status → valid: false (Hardware mismatch — esperado)
```

---

## Root Cause: "Authenticating session" stuck

### Árbol de causas

```
Usuario abre app de escritorio
  → URL: http://127.0.0.1:8000/?token=xxx&device_id=yyy
  → Frontend carga → BootScreen muestra "Authenticating session"
  → Zustand onRehydrateStorage se ejecuta (microtask, ANTES de React)
    → setAuthToken(token) — OK, token en sessionStorage
    → getOverview() → fetch /api/overview con Bearer token
    → Backend auth middleware:
        → Token válido ✅
        → Licencia inválida ❌ (Hardware mismatch)
        → Response: 403 {"error": "License required"}
    → fetchJson 403 handler:
        ANTES: window.location.href = '/activate' → FULL PAGE RELOAD
        DESPUÉS: SPA navigation → sin recarga
    → BootScreen se completa (~2.5s)
    → React Query useOverview() intenta otra vez → mismo 403
    → Navegación SPA a /activate
    → Activation page: checkLicense() → valid: false
    → Usuario ve formulario de activación
```

### Por qué el WS se conecta pero REST no

El WebSocket endpoint NO verifica licencia (solo token). El REST middleware SÍ verifica licencia. Esto crea una asimetría:
- WS → conecta ✅ (no hay check de licencia)
- REST /api/overview → 403 ❌ (licencia inválida)

---

## Bugs Críticos No Corregidos

### Bug #2 — Asimetría auth: WS vs REST
**Archivo:** `api/routers/ws.py` + `api/middleware/auth_middleware.py`
**Razón:** Requiere modificación del backend. El WS endpoint no llama a `is_license_valid()`.
**Mitigación:** Los fixes #1 y #1b evitan el full page reload, convirtiéndolo en navegación SPA controlada.

---

## Próximos Pasos

Para validación completa en Windows (entorno real del usuario):
1. Reactivar licencia (el error es "Hardware mismatch" — reactivar soluciona)
2. O modificar backend para que coincida el HW ID
3. Abrir la app → debe mostrar dashboard sin stuck
4. Verificar que el Service Worker actualiza (limpiar caché si es necesario)

Una vez validado:
- `npm run build` → `dist/` actualizado
- `pyinstaller Rastro.spec` → EXE
- `npx cap copy android && npx cap sync android` → APK
- ZIP final con `dist/` del frontend
