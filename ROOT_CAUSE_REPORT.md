# Root Cause Report: Puerto 5173 en URL del navegador

## Fecha
2026-06-18

## Síntoma
Rastro.exe abre `http://127.0.0.1:5173/?device_id=ADRI-45beac81` en el navegador.
El backend no escucha en el puerto 5173 (ERR_CONNECTION_REFUSED).

---

## Investigación

### 1. Settings.json (descartado)
**Archivo:** `%APPDATA%\Rastro\settings.json`
```json
"backend_port": 8000,
```
El settings persistente TIENE `backend_port: 8000`. No es la fuente del 5173.

### 2. Código fuente actual (HEAD 40f34ba) — NO contiene 5173 en desktop/
- `desktop/main_desktop.py` — usa `settings.get("backend_port", 8000)` y pasa `port` correctamente
- `desktop/browser_opener.py` — `port: int = 8000` como default
- `desktop/serve_frontend.py` — No se usa en PyInstaller
- `launcher/start.py:32` tiene `FRONTEND_PORT = 5173` pero **no está empaquetado en el binario**

### 3. Bytecode del binario NUEVO (desde ZIP RC2) — Confirmado sin 5173
- `desktop.browser_opener` → default argument tuple `(8000, '/', None, None, None, None)`
- `desktop.main_desktop` → contiene entero `8000`, NO contiene entero `5173`

### 4. El binario RC1 SÍ tiene 5173 hardcodeado — **CAUSA RAÍZ**
**Archivo:** `C:\Users\adrie\Rastro-Build\project\desktop\main_desktop.py`
```python
def _open_browser(port: int) -> None:       # ← ACEPTA port como parámetro
    ...
    ctx: dict = {
        "port": 5173,                        # ← IGNORA el parámetro, USA 5173
        ...
    }
```
El código RC1 ignora el `port` recibido y usa `5173` fijo en 6 lugares:

| Archivo | Línea | Código RC1 (bug) |
|---|---|---|
| `main_desktop.py` | 237 | `"port": 5173` en context dict |
| `main_desktop.py` | 275 | `port=5173` en tray open_dashboard |
| `main_desktop.py` | 282 | `port=5173` en tray daily mode |
| `browser_opener.py` | 70 | `port: int = 5173` default en `build_dashboard_url` |
| `browser_opener.py` | 96 | `port: int = 5173` default en `open_dashboard` |
| `serve_frontend.py` | 80 | `--port` default 5173 |

### 5. El ejecutable OLD en el escritorio — **EL QUE SE EJECUTA**
Se encontraron **tres binarios distintos** en la máquina Windows:

| Ubicación | SHA256 | Tamaño | Fecha | Versión |
|---|---|---|---|---|
| `%UserProfile%\Desktop\Rastro.exe` | `31767144...` | 13.2 MB | Jun 12 18:14 | **RC1 (BUG)** |
| `%UserProfile%\Rastro-Build\dist\Rastro\Rastro.exe` | `aa9ed111...` | 15.9 MB | Jun 12 21:21 | **RC1 (BUG)** |
| `%UserProfile%\OneDrive\Desktop\Yo\PAQUETE\Rastro-1.4.0-rc2-final-unified\Windows\Rastro.exe` | `30dfbf74...` | 16.8 MB | Jun 18 01:28 | **RC2 (FIXED)** |

El usuario ejecuta `C:\Users\adrie\Desktop\Rastro.exe` (RC1, bug), no el nuevo del PAQUETE.

### 6. Mecanismo exacto del bug
1. `main()` → `_init_settings()` → `port = 8000` (desde settings.json)
2. `ServerThread(host, port=8000)` → servidor escucha en **8000** ✓
3. `_open_browser(port=8000)` → **ignora el parámetro**, usa `"port": 5173`
4. URL generada: `http://127.0.0.1:5173/?device_id=ADRI-45beac81`
5. Navegador abre 5173 → ERR_CONNECTION_REFUSED (servidor está en 8000)

### 7. Brave Apps shortcut
`C:\Users\adrie\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Brave Apps\Rastro.lnk`
Apunta a Brave Browser con `chrome_proxy.exe` — es un acceso directo PWA creado cuando el usuario abrió `http://127.0.0.1:5173` y Brave ofreció "Instalar como app". Esto perpetúa el 5173 incluso si se arregla el binario.

### 8. Auto-inicio (startup)
`C:\Users\adrie\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Rastro.bat`
```batch
start "" "C:\Users\adrie\Desktop\Rastro\Rastro.exe" -m desktop.main_desktop --no-tray
```
Este archivo ya no funciona porque `C:\Users\adrie\Desktop\Rastro\Rastro.exe` fue eliminado (solo queda `_internal/`).

---

## Conclusión
**No es un bug del código actual.** El código actual (HEAD 40f34ba) y el binario RC2 en PAQUETE tienen la corrección correcta. El usuario está ejecutando el **binario RC1 antiguo** que tiene `5173` hardcodeado en 6 lugares.

## Acciones necesarias
1. Reemplazar `C:\Users\adrie\Desktop\Rastro.exe` (viejo, 13 MB) con el nuevo `Rastro.exe` del PAQUETE (16.8 MB)
2. Eliminar el acceso directo PWA de Brave Apps (apunta a 5173)
3. Actualizar `Rastro.bat` para que apunte al nuevo ejecutable
4. Reconstruir el binario Windows RC2 desde el build pipeline de Windows (por confirmación cruzada)
5. Regenerar el ZIP unificado
