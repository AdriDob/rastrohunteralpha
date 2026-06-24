# CHUNK_AUDIT_REPORT

## Resumen

Se verificaron todos los chunks lazy-loaded del frontend contra el servidor con `_mount_frontend()` activo. Todos responden correctamente como `text/javascript`. El código está sano. La causa del error `application/json` es **ambiental/deployment**, no del código fuente.

---

## Auditoría de chunks

| Chunk | Existe | Ruta física | MIME servido | Status | Tamaño |
|-------|--------|-------------|-------------|--------|--------|
| MissionControl-C-xcIiIE.js | ✅ | `frontend/dist/assets/` | `text/javascript; charset=utf-8` | 200 | 26,384 |
| KPICard-hwM5aC38.js | ✅ | `frontend/dist/assets/` | `text/javascript; charset=utf-8` | 200 | 853 |
| Panel-DIRwhdsd.js | ✅ | `frontend/dist/assets/` | `text/javascript; charset=utf-8` | 200 | 2,431 |
| Badge-CzoNk_7P.js | ✅ | `frontend/dist/assets/` | `text/javascript; charset=utf-8` | 200 | 1,214 |
| index-CwXn44sW.js | ✅ | `frontend/dist/assets/` | `text/javascript; charset=utf-8` | 200 | 455,631 |
| Activation-BsSIivwD.js | ✅ | `frontend/dist/assets/` | `text/javascript; charset=utf-8` | 200 | verificado |
| DailyMode-D3utXl_k.js | ✅ | `frontend/dist/assets/` | `text/javascript; charset=utf-8` | 200 | verificado |
| AttackSurface-D98L6SEJ.js | ✅ | `frontend/dist/assets/` | `text/javascript; charset=utf-8` | 200 | verificado |
| Skeleton-BBrxNivq.js | ✅ | `frontend/dist/assets/` | `text/javascript; charset=utf-8` | 200 | verificado |
| (todos los 44 chunks .js en dist/assets/) | ✅ | — | `text/javascript` | 200 | >0 |

---

## Ruteo verificado

### `_mount_frontend()` en `desktop/main_desktop.py:171-211`

```python
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path:
        file_path = dist_dir / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))  # ← MIME correcto
    if index_path.is_file():
        return FileResponse(str(index_path))      # ← index.html
    return JSONResponse(status_code=404, ...)      # ← application/json
```

- `dist_dir` = `get_frontend_dist_dir()` → `frontend/dist/` (dev) o `frontend_dist/` (frozen)
- `FileResponse` usa `mimetypes.guess_type()` → `.js` → `text/javascript` ✅
- Catch-all **sí existe** y está correctamente registrada en `main_desktop.py:446`

### Middleware de auth (`auth_middleware.py:36-37`)

```python
if not path.startswith("/api/"):
    return await call_next(request)
```

- `/assets/*` NO comienza con `/api/` → pasa sin auth ✅
- middleware no puede producir `application/json` para assets

### Vite config (`frontend/vite.config.ts`)

```typescript
server: { proxy: { '/api': 'http://127.0.0.1:8000' } }
```

- Solo proxea `/api/*`. `/assets/*` se sirve directo ✅

---

## Causa raíz más probable

El error `application/json` ocurre cuando el backend **no tiene montado el frontend**. Específicamente:

1. **Backend standalone**: Si se ejecuta `uvicorn api.main:app` (sin `_mount_frontend()`), no existe ruta para `/assets/*` → FastAPI devuelve 404 con JSON
2. **EXE sin frontend_dist correcto**: Si el PyInstaller no empaqueta `frontend/dist` → `get_frontend_dist_dir()` en frozen apunta a `frontend_dist/` que no existe → catch-all devuelve JSON 404
3. **Service Worker antiguo**: Con el bug #3 original (`cacheFirst`), el SW cacheó respuestas 404 JSON de visitas previas y las sirvió en lugar de ir a la red

### Evidencia

Cuando se usó `run.py --browser` (que llama a `_mount_frontend()`), todos los chunks responden 200 OK con `text/javascript`. Cuando se accedió a `uvicorn api.main:app` sin frontend, los chunks devuelven 404 JSON.

```
$ curl http://127.0.0.1:8095/assets/MissionControl-C-xcIiIE.js
→ 200 OK, Content-Type: text/javascript; charset=utf-8
$ curl http://127.0.0.1:8081/assets/MissionControl-C-xcIiIE.js  (sin frontend mount)
→ 404 Not Found, Content-Type: application/json
```

---

## Corrección aplicada

**Ninguna necesaria en el código.** El fix es asegurar que el frontend esté montado:

- En dev: usar siempre `python run.py --browser` (o `run.py`), **nunca** `uvicorn api.main:app` directamente
- En EXE: validar que `frontend_dist/` esté presente junto al .exe (PyInstaller `--add-data` en `build_windows_exe.py:83`)
- Service Worker: ya corregido de `cacheFirst` → `networkFirst` (bug #3). Si el navegador tiene cache viejo, **limpiar Service Worker** (DevTools → Application → Clear storage)

---

## Próximo paso

Ejecutar `python run.py --browser` y verificar que:

1. ✅ BootScreen completa sin stuck
2. ✅ MissionControl carga sin error MIME
3. ✅ KPICard, Panel, Badge cargan
4. ✅ Dashboard completo renderizado
5. ✅ No hay GlobalErrorBoundary
