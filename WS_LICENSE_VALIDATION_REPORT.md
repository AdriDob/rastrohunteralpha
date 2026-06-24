# WS_LICENSE_VALIDATION_REPORT.md

> Evidencia de la corrección del Bug #7 — WebSocket sin validación de licencia.

---

## Cambio aplicado

**Archivo:** `api/routers/ws.py:28-33`

**Antes:**
```python
user_id = payload.get("sub") or payload.get("user_id")

manager = get_ws_manager()
```

**Después:**
```python
from core_engines.license import is_license_valid
valid_license, _ = is_license_valid()
if not valid_license:
    logger.warning("WS rejected: license required (token valid but no active license)")
    await websocket.close(code=4001, reason="License required")
    return

user_id = payload.get("sub") or payload.get("user_id")

manager = get_ws_manager()
```

## Comportamiento coincidente con REST

El middleware REST (`api/middleware/auth_middleware.py:64-71`) aplica el mismo patrón:

```python
valid_license, _ = is_license_valid()
if not valid_license and path not in PUBLIC_PATHS and not any(
    path.startswith(p) for p in PUBLIC_PREFIXES
):
    return JSONResponse(
        status_code=403,
        content={"error": "License required", ...},
    )
```

**Diferencias:**
- REST retorna `403 + JSON` → el frontend captura `onAuthRedirect('/activate')`
- WS cierra conexión con código `4001 + "License required"` → WebSocket.onclose dispara reconexión que falla con el mismo error, eventualmente se detiene tras 20 intentos

## Verificación

| Escenario | WS antes del fix | WS después del fix |
|---|---|---|
| Token válido + licencia válida | ✅ Conecta | ✅ Conecta |
| Token válido + licencia inválida | ✅ Conecta (BUG) | ❌ Rechaza con 4001 |
| Token inválido + cualquier licencia | ❌ Rechaza con 4001 | ❌ Rechaza con 4001 (sin cambio) |
| Sin token | ❌ Rechaza con 4001 | ❌ Rechaza con 4001 (sin cambio) |

## Logs

```
# Antes: WS conecta aunque licencia sea inválida
[WS] Client connected (user_id=...)

# Después: WS rechazado si licencia inválida
[rastro.api.ws] WARNING: WS rejected: license required (token valid but no active license)
[WS] Client disconnected (code=4001, reason=License required)
```

## Consistencia

REST y WS ahora tienen comportamiento idéntico: ambas capas verifican `is_license_valid()` antes de permitir la operación. Si la licencia es inválida, ambas rechazan la conexión con un mensaje claro.
