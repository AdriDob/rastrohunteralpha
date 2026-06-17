# DESKTOP STARTUP VALIDATION — Rastro v1.4.0-rc1

**Fecha:** 2026-06-17
**Build:** CI rebuild + local (commit d4931dc/24f5ea2)

---

## Fix aplicado

**Archivo:** `desktop/main_desktop.py` — `_open_desktop_window()` y bloque `else` en `main()`

### Problema original
`webview.start(storage_path=None)` retorna inmediatamente sin excepción cuando WebView2 runtime no está instalado en Windows. `_open_desktop_window()` no detectaba esto, retornaba, `main()` ejecutaba cleanup y Python terminaba con exit code 0 — sin ventana, sin backend, sin mensaje.

### Solución implementada
`_open_desktop_window()` ahora:
1. Registra `time.time()` antes de `webview.start()`
2. Crea un `threading.Event` vinculado a `window.closed`
3. Loggea antes y después de `webview.create_window()` y `webview.start()`
4. Si `webview.start()` retorna en menos de 2 segundos **sin** que el usuario cerrara la ventana → retorna `False`
5. Si retorna `False`, `main()` abre el navegador automáticamente y mantiene el backend vivo

### Flujo post-fix

| Escenario | Comportamiento |
|-----------|---------------|
| WebView2 instalado, ventana se abre | ✅ `_open_desktop_window()` retorna `True` (bloquea hasta cerrar) |
| Sin WebView2, `start()` retorna rápido | ✅ `_open_desktop_window()` retorna `False` → browser mode |
| `webview.create_window()` lanza excepción | ✅ `except` captura → retorna `False` → browser mode |
| Usuario cierra ventana en < 2s | ✅ `closed` event → `user_closed.set()` → retorna `True` (exit normal) |
| Browser mode activado | ✅ Backend sigue vivo, tray icon activo, `shutdown_event.wait()` bloquea |

---

## Pruebas

### Unitarias
- `python -m pytest tests/ -q --tb=short` → **159/159 passed**
- `python scripts/prebuild.py` → **16/16 passed**
- `cd frontend && npx tsc --noEmit` → **0 TS errors**

### Build
- Linux PyInstaller: ✅ `dist/Rastro/Rastro` (21 MB ELF)
- Windows CI (GitHub Actions): ✅ `Rastro.exe` (16 MB PE32)
- Android APK: ✅ `dist/rastro-android-debug.apk` (4.2 MB)

### Estructurales (ZIP unificado)
- `Rastro-Windows/Rastro.exe` presente ✅
- `Rastro-Linux/Rastro` (ELF) presente ✅
- `Rastro-Linux/run.sh` presente ✅
- `Rastro-Android/rastro-android-debug.apk` presente ✅
- `Documentacion/` (11 archivos) presente ✅
- `VERSION` = `1.4.0-rc1` ✅
- Sin leaks (`database/`, `logs/`) ✅

---

## Validación E2E Windows (requiere prueba real)

Para marcar Windows como completamente validado, el usuario debe:

1. Descargar `Rastro-1.4.0-rc1-final-unified.zip` (140 MB)
2. Extraer y ejecutar `Rastro-Windows/Rastro.exe`
3. **Sin WebView2**: Verificar que el navegador se abre automáticamente
4. **Con WebView2**: Verificar que la ventana nativa aparece
5. En ambos casos, verificar:
   - Backend inicia (puerto 8000)
   - Frontend carga
   - Se puede crear un target
   - Se puede ejecutar un scan
   - Pipeline funciona

### Criterios de aceptación

| Criterio | Estado |
|----------|--------|
| `.exe` no termina silenciosamente | ✅ **Corregido** (fix en `_open_desktop_window()`) |
| Sin WebView2 → browser | ✅ **Corregido** (fallback automático) |
| Con WebView2 → ventana nativa | ✅ Comportamiento original preservado |
| Backend vivo siempre | ✅ `shutdown_event.wait()` en browser mode |
| Logs claros en `logs/rastro.log` | ✅ Logs antes/después de cada paso de `webview.*` |
| Mensaje "Desktop UI unavailable" | ✅ Loggeado en boot sequence |

---

## ZIP unificado

- `~/Desktop/Rastro-1.4.0-rc1-final-unified.zip` (140 MB, 1428 files)
- `C:\Users\adrie\OneDrive\Desktop\Rastro-1.4.0-rc1-final-unified.zip`
- GitHub Release: `Rastro-1.4.0-rc1-final-unified.zip`
