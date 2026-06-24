# Desktop E2E Validation — v1.4.0-rc2

## Validated Version

| Field | Value |
|---|---|
| **Version** | `v1.4.0-rc2` |
| **Tag** | `v1.4.0-rc2` |
| **Commit** | `40f34ba` |
| **Windows binary** | `Rastro.exe` (16.9 MB, PE32, built by CI Python 3.12 + PyInstaller) |
| **Backend port** | `8000` (single source of truth from `desktop.settings.backend_port`) |
| **Build date** | 2026-06-17 |

## Bug Fixes Applied

| Bug | Root Cause | Fix |
|---|---|---|
| `ERR_CONNECTION_REFUSED` al abrir dashboard | `_open_browser()` ignoraba su parámetro `port` y usaba `port=5173` hardcodeado | `"port": 5173` → `"port": port` en `main_desktop.py:286` |
| `ERR_CONNECTION_REFUSED` desde tray | `_start_tray()` hardcodeaba `port=5173` en Open Dashboard y Open Daily Mode | `port=5173` → `port=api_port` (captura `server.port`) en `main_desktop.py:324,331` |
| Default incorrecto en URL builders | `build_dashboard_url()` y `open_dashboard()` default `5173` | `5173` → `8000` en `browser_opener.py:70,96` |
| Default inconsistente en CLI utility | `serve_frontend.py --port` default `5173` | `5173` → `8000` en `serve_frontend.py:80` |

## Test Results

**Full suite: 170/170 passed** (`pytest tests/ -v`)

### Port Consistency Tests (11 new)

| Test | Result |
|---|---|
| `test_env_config_default_port` — EnvConfig.port == 8000 | ✅ |
| `test_settings_default_port` — DEFAULT_SETTINGS.backend_port == 8000 | ✅ |
| `test_build_dashboard_url_default_port` — URL generada con puerto 8000 | ✅ |
| `test_build_dashboard_url_explicit_port` — port= override funciona | ✅ |
| `test_build_dashboard_url_with_params` — query params correctos | ✅ |
| `test_open_dashboard_default_port` — firma coincide con puerto canónico | ✅ |
| `test_server_thread_stores_port` — ServerThread.expone port | ✅ |
| `test_start_tray_uses_server_port` — código fuente usa server.port, sin 5173 | ✅ |
| `test_open_browser_uses_port_parameter` — código fuente usa port, sin 5173 | ✅ |
| `test_no_hardcoded_5173_in_desktop_code` — barre desktop/*.py | ✅ |
| `test_browser_opener_defaults_match` — ambas funciones mismo default | ✅ |

## E2E Validation Checklist (Windows 11)

### Prerequisites
- [ ] Windows 11 with latest updates
- [ ] No WebView2 runtime (to test browser fallback)
- [ ] Or with WebView2 (to test native window)
- [ ] Extract `Rastro-1.4.0-rc2-final-unified.zip`
- [ ] Navigate to `Windows/`

### Test Sequence

| # | Test | Expected | Actual | Status |
|---|---|---|---|---|
| 1 | Ejecutar `Rastro.exe` | Proceso inicia, sin crash | | ⬜ |
| 2 | Aparece icono en bandeja del sistema | Tray icon visible en system tray | | ⬜ |
| 3 | Click derecho → **Check Status** | Muestra "Running on port 8000" | | ⬜ |
| 4 | **Open Dashboard** | Brave/Chrome abre `http://127.0.0.1:8000/` | | ⬜ |
| 5 | Dashboard carga | Interfaz de Rastro visible, sin errores | | ⬜ |
| 6 | **Open Daily Mode** | Brave/Chrome abre `http://127.0.0.1:8000/daily` | | ⬜ |
| 7 | Daily Mode carga | Daily dashboard visible | | ⬜ |
| 8 | Recargar dashboard varias veces | Conexión estable, sin ERR_CONNECTION_REFUSED | | ⬜ |
| 9 | Verificar `logs/rastro.log` | Backend iniciado en puerto 8000, sin errores | | ⬜ |
| 10 | **Quit Rastro** desde tray | Proceso termina, icono desaparece | | ⬜ |
| 11 | Verificar que no quedan procesos | `tasklist \| findstr Rastro` vacío | | ⬜ |

### Acceptance Criteria (all must pass)

| Criterion | Status |
|---|---|
| ✅ Ejecutar Rastro.exe sin errores | ⬜ |
| ✅ Tray icon aparece | ⬜ |
| ✅ Check Status muestra puerto correcto (8000) | ⬜ |
| ✅ Open Dashboard abre navegador correctamente | ⬜ |
| ✅ Dashboard carga y responde | ⬜ |
| ✅ Open Daily Mode funciona | ⬜ |
| ✅ No hay ERR_CONNECTION_REFUSED | ⬜ |
| ✅ Backend permanece vivo | ⬜ |
| ✅ Cierre limpia servicios correctamente | ⬜ |

## Problems Found

*None during validation.* (Fill in if issues arise.)

## Corrections Applied During Validation

*None required.* (Fill in if issues arise.)

## Final Status

**Desktop Windows Release: PENDING VALIDATION**

Complete the checklist above to mark the release as stable.

## Artifacts

| Asset | Size | Path |
|---|---|---|
| Unified ZIP | ~140 MB | `Rastro-1.4.0-rc2-final-unified.zip` |
| Windows binary | 16.9 MB | `Windows/Rastro.exe` |
| Linux binary | 21 MB | `Linux/Rastro` |
| Android APK | 4.2 MB | `Android/rastro-android-debug.apk` |
