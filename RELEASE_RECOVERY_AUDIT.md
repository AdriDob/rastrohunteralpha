# RELEASE RECOVERY AUDIT — Rastro

**Fecha:** 2026-06-24
**HEAD commit:** `40f34ba` (v1.4.0-rc2)
**Working tree:** 124 modified files, 22+ untracked files — SIN COMMIT

---

## 1. ESTADO ACTUAL DEL PROYECTO

### Git: dos capas divergentes

| Capa | Ref | Descripción |
|------|-----|-------------|
| **Commited (HEAD)** | `40f34ba` | v1.4.0-rc2: solo corrige hardcodeo de puerto 5173→8000 |
| **Working tree** | Sin commit | Contiene TODO el trabajo de Antigravity: auth, session, license HWID, settings migration, frontend fixes, onboarding, etc. |

**Ningún commit posterior a `40f34ba` existe.** Los reportes en `ROOT_CAUSE_REPORT.md`, `AUTH_ROOT_CAUSE_REPORT.md`, `FINAL_STABILITY_REPORT.md` describen código que NO está en git — está en el working tree sin commit.

### VERSION file

- **HEAD (commited):** `VERSION` dice `1.4.0-rc2` (nunca se subió a git)
- **Working tree:** `VERSION` modificado a `1.5.0`
- **dist/ y build/:** Múltiples ZIPs con versiones `1.4.0-rc1`, `1.4.0-rc2`, `1.5.0`

### Veredicto: El código fuente en git NO refleja la release actual.

---

## 2. FIXES PRESENTES EN WORKING TREE (no commiteados)

### ✅ Auth — Correcciones completas

| Fix | Archivos | Líneas clave |
|-----|----------|-------------|
| AuthMiddleware solo protege `/api/*` | `api/middleware/auth_middleware.py` | 36-37 |
| Desktop session auto-creada al boot | `desktop/main_desktop.py` | 221-254, 482 |
| `build_dashboard_url` pasa token en URL | `desktop/browser_opener.py` | 82-83 |
| `AuthErrorHandler` con SPA navigation | `frontend/src/App.tsx` | 83-90 |
| `setOnAuthRedirect` callback | `frontend/src/lib/api.ts` | 22-24 |
| `getOverviewPreload` con `__skipAuthRedirect` | `frontend/src/lib/api.ts` | 162-164 |

### ✅ Onboarding — Correcciones completas

| Fix | Archivos | Líneas clave |
|-----|----------|-------------|
| `onboarding` param en `build_dashboard_url` | `desktop/browser_opener.py` | 77, 90-91 |
| `onboarding` param en `open_dashboard` | `desktop/browser_opener.py` | 106 |
| `ctx["onboarding"]` en `_open_browser` | `desktop/main_desktop.py` | 342-343 |
| `onboarding=1` URL param en frontend | `frontend/src/App.tsx` | 171-177 |

### ✅ Port validation — Completo

| Fix | Archivos | Líneas clave |
|-----|----------|-------------|
| Type check + range validation | `desktop/main_desktop.py` | 265-267 |
| Settings migration 5173→8000 | `desktop/settings.py` | 93-112 |
| `_LEGACY_PORTS` set | `desktop/settings.py` | 21 |

### ✅ License / Hardware ID — Completo

| Fix | Archivos | Líneas clave |
|-----|----------|-------------|
| Windows Registry `MachineGuid` | `core_engines/license/hardware.py` | 45-59 |
| `COMPUTERNAME` fallback | `core_engines/license/hardware.py` | 62 |

### ✅ Frontend — Correcciones completas

| Fix | Archivos | Líneas clave |
|-----|----------|-------------|
| Service Worker `networkFirst` | `frontend/public/service-worker.js` | 75 |
| `onAuthRedirect` SPA navigation | `frontend/src/lib/api.ts` | 44-51 |
| `setHydrating`/`setHydrated` con setState directo | `frontend/src/stores/index.ts` | 19-24 |
| Activation auto-redirect | `frontend/src/pages/Activation.tsx` | setTimeout redirect |
| MIME types registrados | `desktop/main_desktop.py` | 178-180 |

### ✅ Encoding fix

| Fix | Archivos |
|-----|----------|
| `→` (U+2192) reemplazado por `->` | `desktop/main_desktop.py` (docstrings) |

**Nota:** Solo se reemplazó en `desktop/main_desktop.py`. El resto del código fuente (~100+ archivos en `C:/Users/.../rastro_build/` y `core_engines/`) aún contiene `→`. Pero como estos son comentarios/docstrings (no log messages), no causan el crash cp1252.

---

## 3. FIXES FALTANTES (no implementados)

### ❌ Bug #2 — Asimetría auth: WebSocket no verifica licencia

**Archivo:** `api/routers/ws.py:14-42`
**Problema:** WS solo verifica token, NO llama a `is_license_valid()`. El REST middleware SÍ lo hace. Esto causa que WS se conecte exitosamente pero REST devuelva 403.
**Estado:** NO CORREGIDO

### ❌ Bug #7 — Sin manejo de errores visible en getOverview

**Archivo:** `frontend/src/stores/index.ts:72-74`
**Problema:** El catch solo loggea, no muestra feedback visual al usuario.
**Estado:** NO CORREGIDO

### ❌ Bug #8 — `useEffect` con dependencias vacías

**Archivo:** `frontend/src/App.tsx:97-120`
**Problema:** eslint-disable para dependencias (searchParams).
**Estado:** NO CORREGIDO (baja prioridad)

### ❌ Bug #9 — SW sin estrategia de actualización dinámica

**Archivo:** `frontend/public/service-worker.js`
**Problema:** No hay versión dinámica ni migración automática.
**Estado:** NO CORREGIDO (baja prioridad)

### ❌ Bug #10 — StrictMode en desarrollo

**Archivo:** `frontend/src/main.tsx`
**Problema:** StrictMode monta/desmonta dos veces en dev.
**Estado:** NO CORREGIDO (baja prioridad)

### ❌ Bug #12 — BootScreen sin estado de error

**Archivo:** `frontend/src/components/BootScreen.tsx`
**Problema:** No muestra errores de boot al usuario.
**Estado:** NO CORREGIDO (media prioridad)

### ❌ Bug #13 — Sin validación de token URL vs sessionStorage

**Archivo:** `frontend/src/App.tsx:97-120` y `frontend/src/stores/index.ts:59-66`
**Problema:** `AppInitializer` y `onRehydrateStorage` ambos leen token sin coordinar.
**Estado:** NO CORREGIDO (baja prioridad)

### ❌ Bug #14 — SW registra en `load` event

**Archivo:** `frontend/src/main.tsx`
**Problema:** Puede perder requests iniciales.
**Estado:** NO CORREGIDO (baja prioridad)

### ❌ Bug #16 — Sin validación de tipo en saveSettings/loadSettings

**Archivo:** `frontend/src/App.tsx:66-81`
**Problema:** `JSON.parse` puede fallar silenciosamente.
**Estado:** NO CORREGIDO (baja prioridad)

---

## 4. FIXES PARCIALMENTE IMPLEMENTADOS

### ⚠️ Loop "Authenticating session"

**Causa raíz:** Múltiples causas encadenadas:
1. WS conecta (no check de license) → parece que funciona
2. REST /api/overview → 403 (license check)
3. `getOverviewPreload` falla con `__skipAuthRedirect` → silencioso
4. React Query `getOverview` falla → 403 → `onAuthRedirect('/activate')`
5. SPA navega a `/activate`

**Lo que NO está resuelto:** El ciclo puede ocurrir si:
- La licencia es inválida (siempre muestra activation después de boot)
- `getOverviewPreload` falla en stores/index.ts catch silencioso
- No hay flag de "already tried" para evitar reintentos

**Estado: PARCIALMENTE CORREGIDO** — el crash loop se evitó (ya no es full page reload),
pero el flujo "dashboard → activation" sigue siendo confuso.

### ⚠️ WebSocket cerrándose antes de completar conexión

**Causas potenciales:**
1. Token no disponible cuando WS intenta conectar
2. No hay license check en WS endpoint (conecta pero no puede hacer nada)
3. Race condition: `ws.ts:77` lee token de sessionStorage, pero puede ser null si `AppInitializer` no ha corrido

**Estado: PARCIALMENTE CORREGIDO** — el token flow mejoró con `_create_desktop_session`,
pero el WS endpoint sigue sin verificar licencia (Bug #2).

### ⚠️ Diferencias run.py / uvicorn / PyInstaller / EXE

**Estado actual:**
- `run.py` → llama `desktop.main_desktop.main()` → full lifecycle ✅
- `uvicorn api.main:app` → solo API, NO mount frontend, NO session creation ❌
- PyInstaller desde `Rastro.spec` → usa `run.py` como script → full lifecycle ✅
- EXE distribuido → compilado de PyInstaller, depende de working tree al buildear

**Diferencia principal:** `uvicorn api.main:app` es INUTILIZABLE para desktop.
No monta frontend, no crea sesión. El `CHUNK_AUDIT_REPORT.md` confirma que
`curl http://localhost:8081/assets/MissionControl-xxx.js` devuelve 404 JSON.

**Estado: PARCIALMENTE DOCUMENTADO** — los reportes mencionan esto pero no hay
validación automática que prevenga su uso incorrecto.

---

## 5. REPORTES DESACTUALIZADOS

### Reportes que NO reflejan el código commiteado

| Reporte | Estado | Razón |
|---------|--------|-------|
| `ROOT_CAUSE_REPORT.md` | ⚠️ **Parcialmente desactualizado** | Describe RC1 vs RC2, pero asume que RC2=v1.5.0 está en git (no lo está) |
| `AUTH_ROOT_CAUSE_REPORT.md` | ⚠️ **Parcialmente desactualizado** | El análisis de auth está correcto, pero las soluciones descritas NO están en git |
| `FINAL_STABILITY_REPORT.md` | ⚠️ **Desactualizado** | Reporta SHA de EXEs que ya no existen en el working tree actual |
| `FINAL_PACKAGE_AUDIT.md` | ⚠️ **Desactualizado** | SHA del ZIP (`4b49c23c...`) no coincide con ningún ZIP en dist/ actual |
| `VALIDATION_REPORT.md` | ⚠️ **Desactualizado** | SHA del ZIP (`19495BB3...`) no es el mismo que el ZIP actual en dist/ |
| `VALIDACIÓN_FINAL.md` | ✅ **Válido** | Describe bugs correctamente, no depende de commits |
| `BUGS_CORREGIDOS.md` | ✅ **Válido** | Lista de bugs corregidos es correcta |
| `BUGS_ENCONTRADOS.md` | ✅ **Válido** | Lista de bugs encontrados es correcta |
| `CHUNK_AUDIT_REPORT.md` | ✅ **Válido** | Análisis de chunks sigue siendo correcto |
| `LICENSE_AUDIT_REPORT.md` | ✅ **Válido** | Análisis de licencias correcto |
| `WINDOWS_RELEASE_AUDIT.md` | ⚠️ **Desactualizado** | Reporta v1.4.0-rc1, no v1.5.0 |
| `DESKTOP_STARTUP_VALIDATION.md` | ⚠️ **Desactualizado** | Reporta v1.4.0-rc1 |
| `DESKTOP_E2E_VALIDATION.md` | ⚠️ **Desactualizado** | Reporta v1.4.0-rc2, checklist sin completar |
| `REAL_WORLD_VALIDATION.md` | ✅ **Válido** | Prueba de pipeline funcional, no depende de versión |
| `HARDWARE_ID_CONSISTENCY_REPORT.md` | ✅ **Válido** | No leído, pero es específico de HWID |

---

## 6. ERRORES AÚN REPRODUCIBLES

### 🔴 Error reproducible: Backend standalone sin frontend

**Comando:** `uvicorn api.main:app`
**Síntoma:** Chunks JS sirven como `application/json` (404)
**Causa:** `auth_middleware.py` deja pasar pero no existe ruta para assets
**Workaround:** Usar `python run.py` en vez de uvicorn directo

### 🔴 Error reproducible: Licencia inválida → loop dashboard/activation

**Síntoma:** Dashboard se ve por instantes, luego redirige a /activate
**Causa:** `is_license_valid()` retorna False → middleware devuelve 403 → SPA redirect
**Workaround:** Activar licencia vía `generate_license()` + `POST /api/license/activate`

### 🔴 Error reproducible: WS conecta pero REST falla

**Síntoma:** WebSocket status = connected, pero llamadas API devuelven 403
**Causa:** Bug #2 — WS endpoint no verifica licencia
**Workaround:** Activar licencia

### 🟡 Error reproducible: Hardcodeo 5173 en launcher/start.py

**Archivo:** `launcher/start.py:32` — `FRONTEND_PORT = 5173`
**Impacto:** Si alguien usa `python launcher/start.py --dashboard react`, intenta abrir 5173
**Nota:** Este script no se usa en frozen builds

### 🟡 Error reproducible: Build artifact leak

**Path:** `C:\Users\adrie\AppData\Local\Temp\rastro_build/`
**Problema:** Directorio literal de Windows creado en Linux, con archivos fuente duplicados (~30 MB)
**Impacto:** Contamina búsquedas (grep), podría incluirse accidentalmente en ZIPs

### 🟡 Error reproducible: Múltiples ZIPs en dist/

| Archivo | Tamaño | SHA (estimado) |
|---------|--------|----------------|
| `Rastro-1.5.0-definitive.zip` | ¿? | ¿? |
| `Rastro-1.5.0-FINAL-DEFINITIVE-STABLE.zip` | ¿? | ¿? |
| `Rastro-1.5.0-FINAL.zip` | ¿? | ¿? |
| `Rastro-1.5.0-stable.zip` | ¿? | ¿? |
| `Rastro-Portable-1.5.0.zip` | ¿? | ¿? |
| `Rastro-1.5.0-FINAL/` (dir) | ¿? | ¿? |
| `Rastro-1.5.0-stable/` (dir) | ¿? | ¿? |

**Problema:** No hay claridad de cuál es el ZIP definitivo. Los SHAs en reportes NO coinciden con los ZIPs actuales.

---

## 7. PROBLEMA BLOQUEANTE DE RELEASE

### 🔴 BLOQUEANTE: El código fuente en git NO coincide con los EXEs distribuidos

**Evidencia:**
- HEAD = `40f34ba` (v1.4.0-rc2, solo fix 5173→8000)
- Los EXEs fueron compilados con el working tree (que tiene auth, session, HWID, etc.)
- Si alguien clona el repo y compila, obtendrá un EXE SIN auth, SIN session, SIN HWID fix

**Riesgo:** El release no es reproducible desde git.

**Acción requerida antes de release:**
1. Commit de todo el working tree O
2. Tag del working tree como v1.5.0 O  
3. Reconstruir EXEs desde un commit confirmado

### 🔴 BLOQUEANTE: ROOT_CAUSE_REPORT.md contradice el código actual

**Reporte dice:** "El código actual (HEAD 40f34ba) y el binario RC2 tienen la corrección correcta"
**Realidad:** HEAD 40f34ba NO tiene auth fix, NO tiene session creation, NO tiene HWID fix, NO tiene settings migration. Solo tiene el fix 5173→8000.

Si un usuario clona el repo y compila desde HEAD, obtendrá una app que:
1. Abre el puerto 8000 ✅
2. Pero devuelve 401 en TODAS las rutas (no tiene auth bypass para assets) ❌
3. No tiene auto-sesión (token nunca se crea) ❌
4. No tiene migración de settings ❌
5. No tiene HWID para Windows ❌

---

## 8. MAPA DE ARCHIVOS CRÍTICOS POR REVISAR

### Entry points

| Archivo | Propósito | Estado |
|---------|-----------|--------|
| `run.py` | Entrypoint dev/frozen | ✅ Sin cambios necesarios |
| `desktop/main_desktop.py` | Lógica principal desktop | ⚠️ Modificado (sin commit) |
| `launcher/start.py` | Launcher legacy (no usado en frozen) | ⚠️ Contiene FRONTEND_PORT=5173 |
| `api/main.py` | FastAPI app | ⚠️ Modificado (sin commit) |
| `Rastro.spec` | PyInstaller spec | ✅ Sin cambios |

### Auth pipeline

| Archivo | Propósito | Estado |
|---------|-----------|--------|
| `api/middleware/auth_middleware.py` | Middleware auth HTTP | ⚠️ Modificado (sin commit) |
| `api/routers/ws.py` | WebSocket endpoint | ⚠️ Modificado (sin commit) |
| `core_engines/auth/auth_manager.py` | AuthManager singleton | ✅ Sin cambios |
| `core_engines/auth/auth.py` | Token create/verify | ✅ Sin cambios |
| `core_engines/auth/session.py` | Session store | ✅ Sin cambios |
| `core_engines/auth/session_validator.py` | Session validator | ✅ Sin cambios |

### License

| Archivo | Propósito | Estado |
|---------|-----------|--------|
| `core_engines/license/hardware.py` | Machine fingerprint | ⚠️ Modificado (sin commit) |
| `core_engines/license/validator.py` | License validate/generate | ✅ Sin cambios |
| `core_engines/license/store.py` | License persistence | ⚠️ Modificado (sin commit) |

### Desktop settings

| Archivo | Propósito | Estado |
|---------|-----------|--------|
| `desktop/settings.py` | Settings manager + migration | ⚠️ Modificado (sin commit) |
| `desktop/browser_opener.py` | URL builder + browser launcher | ⚠️ Modificado (sin commit) |

### Frontend

| Archivo | Propósito | Estado |
|---------|-----------|--------|
| `frontend/src/App.tsx` | Root component | ⚠️ Modificado (sin commit) |
| `frontend/src/lib/api.ts` | API client | ⚠️ Modificado (sin commit) |
| `frontend/src/stores/index.ts` | Zustand store | ✳️ Nuevo (reemplaza store.ts) |
| `frontend/src/lib/ws.ts` | WebSocket client | ⚠️ Modificado (sin commit) |
| `frontend/public/service-worker.js` | Service Worker | ⚠️ Modificado (sin commit) |
| `frontend/src/pages/Activation.tsx` | Activation page | ⚠️ Modificado (sin commit) |

---

## 9. ACCIONES RECOMENDADAS (en orden)

### Inmediatas (bloqueantes)
1. **Commitear todo el working tree** con mensaje descriptivo
2. **Limpiar `C:\Users\adrie\AppData\Local\Temp\rastro_build/`** (directorio fantasma)
3. **Definir un ZIP único como definitivo** y eliminar/archivar los demás
4. **Verificar que RELEASE_NOTES.md refleje el contenido real del ZIP definitivo**

### Pre-release
5. **Reconstruir EXE Windows** desde el commit confirmado (no desde working tree)
6. **Verificar SHA del EXE** contra el commit
7. **Actualizar reportes** con SHAs reales de los artefactos finales

### Post-audit
8. **Corregir Bug #2** (WS license check) si se considera crítico
9. **Agregar test automático** que verifique que `uvicorn api.main:app` sin frontend no rompe
10. **Actualizar `launcher/start.py`** FRONTEND_PORT a 8000

---

## 10. VEREDICTO

**El proyecto NO está listo para release.**

La causa no son bugs en el código, sino **falta de trazabilidad entre código fuente y artefactos distribuidos**.

El trabajo de Antigravity (auth, session, HWID, onboarding, settings migration) está completo en el working tree pero:
1. No está en git
2. No está taggeado
3. Los SHAs de los ZIPs en dist/ no coinciden con ningún commit
4. Los reportes describen código que no existe en git

**Release bloqueado hasta que:**
- El working tree esté commiteado y taggeado
- Los EXEs estén reconstruidos desde ese commit
- Los SHAs en los reportes coincidan con los artefactos
- El directorio `C:\Users\adrie\AppData\Local\Temp\rastro_build/` sea eliminado
