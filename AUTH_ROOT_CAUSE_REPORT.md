# Auth Root Cause Report — Rastro v1.5.0

**Date:** 2026-06-18
**Commit:** 40f34ba

---

## Problem Statement

Multiple endpoints return `401 Unauthorized` in Desktop mode. The Dashboard, Daily Mode, assets, and dynamic imports all fail because the frontend never obtains a valid session token. The `AuthMiddleware` enforces Bearer token authentication on every request, including frontend static assets, but the desktop never creates a token to pass to the frontend.

---

## 1. ¿Cómo debería autenticarse Desktop?

El desktop debería autenticarse automáticamente al iniciar, sin intervención del usuario. Dado que la API y el frontend corren en el mismo proceso (uvicorn in-process), el desktop tiene acceso directo al `AuthManager` (singleton in-memory) y puede crear una sesión antes de abrir el navegador.

## 2. ¿Quién crea el token?

El `AuthManager` (`core_engines/auth/auth_manager.py`) crea tokens HMAC-SHA256. La función `SessionStore.create_session()` (línea 61) genera un par session_token + refresh_token.

## 3. ¿Cuándo se crea?

**Nunca en el flujo desktop.** El token solo se crea cuando un cliente HTTP llama a `POST /api/auth/login` (un endpoint público). El desktop no hace esta llamada ni llama a `AuthManager.authenticate()` directamente.

## 4. ¿Dónde se almacena?

El `session_token` se almacena en `settings.json` (`~/.config/rastro/settings.json`), campo `"session_token"`. Por defecto es `null` (definido en `desktop/settings.py:45`). También se persiste en `SessionStore` (archivo `sessions.json`).

## 5. ¿Cómo llega al frontend?

El `_open_browser()` en `main_desktop.py:288` lee `settings.get("session_token")`. Si tiene valor, lo pasa como query param `?token=xxx` en la URL del dashboard (`browser_opener.py:80-81`). El frontend `App.tsx:86` lo extrae de `searchParams` y lo guarda en `sessionStorage` como `rastro-token`. **Pero como `session_token` es `null`, nunca se agrega a la URL.**

## 6. ¿Qué rutas requieren auth?

Todas las rutas que no están en `PUBLIC_PATHS` ni `PUBLIC_PREFIXES` de `auth_middleware.py:12-24`:

**Públicas:**
- `/api/health`, `/api/version`, `/api/docs`, `/api/openapi.json`, `/api/redoc`
- `/api/auth/*`, `/api/license/*`

**Protegidas (requieren Bearer token):**
- `/api/targets/*`, `/api/endpoints/*`, `/api/findings/*`, `/api/evidence/*`
- `/api/opportunities/*`, `/api/daily/*`, `/api/overview/*`
- `/api/system/*`, `/api/operations/*`, `/api/execution/*`
- Y **TODAS las demás rutas que no comiencen con `/api/`** incluyendo:
  - `/` (página principal HTML)
  - `/assets/*` (JS, CSS, imágenes — build de Vite)
  - `/vite.svg`, `/favicon.ico`
  - Cualquier ruta SPA como `/daily`, `/settings`, etc.

## 7. ¿Qué rutas no deberían requerir auth?

**Los assets estáticos del frontend NO deberían requerir autenticación.** Esto incluye:
- `/` → index.html
- `/assets/*` → JS, CSS, fuentes, imágenes del build de Vite
- Cualquier archivo servido desde `frontend_dist/`

Esto es un **problema de diseño del middleware**: la distinción entre "protegido" y "público" se basa en listas fijas de paths, no en el prefijo `/api/`. El middleware atrapa TODAS las rutas, incluyendo assets estáticos que el frontend necesita para cargar.

## 8. ¿Por qué /assets recibe 401?

`AuthMiddleware.dispatch()` (línea 28) procesa TODOS los requests. Cuando el navegador pide `/assets/index-abc123.js`:
- La ruta NO está en `PUBLIC_PATHS`
- NO comienza con ningún `PUBLIC_PREFIX`
- No hay header `Authorization: Bearer` (es una petición de página normal)
- → Retorna `401 {"error": "Authorization header required"}`

**Evidencia:** El middleware `auth_middleware.py:37-44`:
```python
auth_header = request.headers.get("Authorization", "")
token = auth_header.removeprefix("Bearer ").strip()
if not token:
    return JSONResponse(status_code=401, content={"error": "Authorization header required"})
```

## 9. ¿Por qué Daily Mode recibe 401?

Cuando el frontend intenta cargar `/daily`:
1. El navegador navega a `http://127.0.0.1:8000/daily`
2. El middleware ve la ruta `/daily` → no es pública → no hay token → 401
3. La SPA nunca carga, por lo que nunca se extrae un token de la URL
4. Incluso si la SPA cargara, la llamada a `GET /api/daily/briefing` también requiere auth y fallaría con 401

## 10. ¿Por qué Dashboard recibe 401?

Mismo problema que `/daily`. La ruta `/` (raíz) está protegida. Aunque se pase `?token=xxx` en la URL, el middleware no inspecciona query params, solo el header `Authorization`. El navegador no envía `Authorization` en navegación normal.

---

## Flujo de Ejecución (Actual)

```
main_desktop.py::main()
  → uuid1 en background thread en 127.0.0.1:8000
  → Health check OK (usa /api/health que es público)
  → settings.session_token = None (default)
  → _open_browser(port)
    → build_dashboard_url(token=None) → no agrega ?token= a la URL
    → webbrowser.open("http://127.0.0.1:8000/")
      → Navegador pide GET /
      → AuthMiddleware: path="/", no es pública, no hay Authorization
      → 401 {"error": "Authorization header required"}
      → El navegador recibe JSON, no HTML → pantalla en blanco/error
```

---

## Archivos Afectados

| Archivo | Línea(s) | Problema |
|---|---|---|
| `api/middleware/auth_middleware.py` | 12-24, 37-44 | Middleware protege rutas no-API (assets, SPA) que no pueden llevar header Authorization |
| `desktop/main_desktop.py` | 274-305 | `_open_browser()` espera que `session_token` exista en settings, pero nunca se crea |
| `desktop/settings.py` | 45 | `session_token: None` por defecto — nunca se actualiza en el flujo desktop |
| `desktop/browser_opener.py` | 80-81 | Solo agrega `?token=` si `token` es truthy; como es None, no se agrega |
| `frontend/src/App.tsx` | 86-91 | Extrae token de URL params, pero la página nunca carga porque el middleware devuelve 401 |

---

## Impacto

- **Total:** El producto desktop es inutilizable sin autenticación manual.
- **401 en:** `/`, `/daily`, `/assets/*`, todas las rutas SPA y APIs privadas
- **Falsa apariencia de funcionamiento:** El health check pasa (`/api/health` es público), el server inicia, el lifecycle log se ve bien. Pero el frontend nunca carga.
- **Regresión desde v1.4:** El middleware auth se agregó sin considerar el flujo desktop local (no hay login manual posible).

---

## Solución Mínima

### Cambio 1: AuthMiddleware — solo proteger rutas /api/

`api/middleware/auth_middleware.py`: Agregar early return para rutas que no comienzan con `/api/`.

```python
# Solo proteger rutas de API. Assets y SPA no requieren auth.
if not path.startswith("/api/"):
    return await call_next(request)
```

**Justificación:** No hay ningún endpoint funcional fuera de `/api/`. Las rutas raíz (`/`, `/{path}`) son solo para servir archivos del frontend.

### Cambio 2: Desktop — crear sesión al iniciar

`desktop/main_desktop.py::main()`: Después del health check y antes de abrir UI, crear sesión vía `AuthManager.authenticate()` y guardar tokens en settings. `_open_browser()` ya lee `session_token` de settings, por lo que lo pasará en la URL automáticamente.

### Seguridad

- El server bindea en `127.0.0.1` → solo accesible desde la máquina local
- CORS está restringido a `localhost:8000` y `app://` en modo desktop
- Las APIs siguen protegidas con Bearer token
- El token se genera con HMAC-SHA256, 24h TTL
- No hay bypass de seguridad para acceso remoto
