# REALITY_MAP — Mapeo de todas las versiones de realidad

## 1. Versión en Git (commiteada)

| Campo | Valor |
|---|---|
| HEAD commit | `40f34ba` |
| Tag | `v1.4.0-rc2` |
| Mensaje | `fix hardcoded port 5173 → 8000 in _open_browser, _start_tray, browser_opener defaults` |
| VERSION (HEAD) | `1.4.0-rc2` (derivado del tag, no hay archivo VERSION en HEAD) |

## 2. Versión en Working Tree (NO commiteada)

| Campo | Valor |
|---|---|
| Archivos modificados respecto a HEAD | 124 |
| Archivos nuevos (untracked) | 355 |
| VERSION (archivo local) | `1.5.0` |
| Estado del working tree | **124 fixes sin commit**: auth middleware, desktop session, HWID, settings migration, onboarding, WS, chunks, MIME, sidebar, report detail, responsive layouts, stores, etc. |

### Archivos modificados clave

| Archivo | Cambio esperado |
|---|---|
| `api/middleware/auth_middleware.py` | Bypass de auth para endpoints non-API |
| `api/main.py` | Agregado middleware y CORS |
| `api/routers/ws.py` | Sin fix de licencia (Bug #2) |
| `api/routers/overview.py` | getOverviewPreload |
| `desktop/main_desktop.py` | _create_desktop_session(), port validación, settings migration |

### Archivos nuevos clave

| Archivo | Propósito |
|---|---|
| 14+ reportes MD | ROOT_CAUSE_REPORT, FINAL_STABILITY_REPORT, VALIDATION_REPORT, etc. |
| `api/routers/discovery.py` | Nuevo módulo |
| `core_engines/engine/correlation.py` | Nuevo módulo |
| `core_engines/intelligence/bounty_intel.py` | Nuevo módulo |

## 3. Versiones en EXE

### EXE A — "release / final"

| Archivo | SHA256 | Tamaño |
|---|---|---|
| `dist/release/Rastro-Desktop-1.5.0/Rastro.exe` | `be1be8b0c77a36c2e56e87dd4b146d5c7a7e34b2abd2ec65c89c84d85236a2db` | 17.2 MB |
| `dist/final/Windows/Rastro-Desktop-1.5.0/Rastro.exe` | `be1be8b0c77a36c2e56e87dd4b146d5c7a7e34b2abd2ec65c89c84d85236a2db` | 17.2 MB |

**IDÉNTICOS** → mismas fuentes, mismo build.

Checksum SHA256 del manifiesto `dist/final/Checksums/`: **coincide**.

### EXE B — "FINAL" (diferente)

| Archivo | SHA256 | Tamaño |
|---|---|---|
| `dist/Rastro-1.5.0-FINAL/Windows/Rastro.exe` | `744755c6630424d4a08e99d80a80f1f0d7159d32c6c0d3b8bf33b5bea56c27c7` | 53.2 MB |

**3× más grande que EXE A**. Distinto build, posiblemente incluye más dependencias o es una compilación diferente.

### Conclusión EXE

**3 archivos EXE, 2 builds distintos**. Build más pequeño (17.2 MB) es el referenciado en el manifiesto `dist/final/`. Build más grande (53.2 MB) sin documentación.

## 4. Versiones en ZIP

| Archivo | SHA256 | Tamaño | Contenido |
|---|---|---|---|
| `dist/Rastro-1.5.0-FINAL-DEFINITIVE-STABLE.zip` | `6ad709128eb8eb07488d58b0056c6dedda16c5ac48fc33f24b562496221d6fc4` | ~57 MB | ZIP con EXE+APK+Docs |
| `dist/Rastro-1.5.0-FINAL.zip` | `88569de4441f85dc76149cb607b96a52287bf241d6b5a4fdb12aaa67a28b2fe1` | ~57 MB | ZIP con EXE+APK+Docs |
| `dist/Rastro-1.5.0-definitive.zip` | `34292177166ba25ef86b880e5cb77fb7a919386872d7097a3348b0771df33fc1` | ~94 MB | ZIP más grande |
| `dist/Rastro-1.5.0-stable.zip` | `a0fa374a811697689cc01a35b3cfa47c72114897c200447354ea255da3f08a20` | ~94 MB | ZIP más grande |
| `dist/Rastro-Portable-1.5.0.zip` | `6ab42a202781dd01911b50a3e6407f8221ac7cb1e72b47323eaf20cf6a9e2243` | ~90 MB | Versión portable |
| `build/Rastro-1.5.0-stable.zip` | `de0de14a338476b373a7e60536858a7be6041579276732bef1e0759fc13a0cfa` | — | ZIP en build/ |

**6 ZIPs, 6 SHA256s distintas. Ningún ZIP coincide con otro.**

### Comparación con reportes existentes

| Reporte | SHA citado | ¿Existe en algún ZIP actual? |
|---|---|---|
| `FINAL_PACKAGE_AUDIT.md` | `4b49c23c...` | ❌ NO encontrado |
| `VALIDATION_REPORT.md` | no especifica SHA | N/A |
| `FINAL_STABILITY_REPORT.md` | no especifica SHA | N/A |
| Manifiesto `dist/final/Checksums/Rastro-1.5.0-FINAL.sha256` | `be1be8b0...` (EXE), `ac82c9fa...` (APK) | ✅ EXE SHA coincide con release/final |

**El ZIP `dist/Rastro-1.5.0-FINAL-DEFINITIVE-STABLE.zip` NO existe en ningún SHA mencionado en reportes.**

## 5. Versiones en APK

### Grupo A — APK pequeño (4.40 MB)

| Archivo | SHA256 |
|---|---|
| `dist/release/Rastro-Android-1.5.0.apk` | `413768a60af2cd52c5f3a3ef6ef8ecc76a962e6dfe2f5e2d512a3407de5e37fb` |
| `dist/Rastro-1.5.0-stable/Android/rastro-android-debug.apk` | `413768a60af2cd52c5f3a3ef6ef8ecc76a962e6dfe2f5e2d512a3407de5e37fb` |
| `dist/rastro-android-debug.apk` | `413768a60af2cd52c5f3a3ef6ef8ecc76a962e6dfe2f5e2d512a3407de5e37fb` |

**3 copias idénticas** del mismo APK debug.

### Grupo B — APK mediano (4.56 MB)

| Archivo | SHA256 |
|---|---|
| `dist/final/Android/Rastro-1.5.0.apk` | `ac82c9fa2bfcfcc7e15d7daa32ad39b9804629332fa6e6fc6d771d7817911129` |
| `dist/android/Rastro-debug.apk` | `ac82c9fa2bfcfcc7e15d7daa32ad39b9804629332fa6e6fc6d771d7817911129` |
| `android/app/build/outputs/apk/debug/app-debug.apk` | `ac82c9fa2bfcfcc7e15d7daa32ad39b9804629332fa6e6fc6d771d7817911129` |

**3 copias idénticas** del build directo de Android Studio/Gradle.

### Grupo C — APK único (4.56 MB)

| Archivo | SHA256 |
|---|---|
| `dist/Rastro-1.5.0-FINAL/Android/Rastro.apk` | `fb5ae8081ec80ec3a7b64589df8ae735c16a519142bf46be923141d8cb0a0e13` |

**APK diferente** dentro del ZIP `Rastro-1.5.0-FINAL.zip`.

### Conclusión APK

7 archivos APK, **3 builds distintos**. Manifiesto `dist/final` referencia SHA `ac82c9fa...` (Grupo B).

## 6. Artefactos temporales contaminantes

| Ruta | Tamaño | Archivos | Origen |
|---|---|---|---|
| `./C:\Users\adrie\AppData\Local\Temp\rastro_build/` | 537 MB | 366 | Build fallido que dejó directorio con ruta literal de Windows en Linux. Contiene copia completa del source tree, `run.py`, `Rastro.spec`, directorios `ai/`, `api/`, `core_engines/`, `frontend/` |

## 7. Especificaciones de Build (spec files)

| Archivo | Entrypoint | ¿Correcto? |
|---|---|---|
| `Rastro.spec` | `run.py` | ✅ Correcto |
| `dist/Rastro-1.5.0-stable/config/Rastro.spec` | Probablemente `run.py` | ✅ |
| `C:\Users\...\rastro_build/Rastro.spec` | `run.py` | ✅ (copia) |
| `scripts/build_windows_exe.py` (línea 109) | `desktop/main_desktop.py` | ❌ **INCORRECTO** — bypass de run.py |

## 8. Scripts de Build

| Script | Entrypoint | ¿Reproducible? |
|---|---|---|
| `build_windows_v15.ps1` | `Rastro.spec` → `run.py` | ✅ Correcto |
| `scripts/build_windows_exe.py` | `main_desktop.py` | ❌ Incorrecto |
| `scripts/build_android.py` | Capacitor/Gradle | ⚠️ No verificado |

## 9. Versión en ejecución directa

| Método | Entrypoint | Monta frontend | Crea sesión desktop |
|---|---|---|---|
| `python run.py` | `run.py` | ✅ `_mount_frontend()` | ❌ (es API pura) |
| `uvicorn api.main:app` | `api.main` | ❌ No | ❌ No |
| `python desktop/main_desktop.py` | `main_desktop.py` | ❌ No (usa settings) | ✅ |
| EXE `dist/release/Rastro.exe` | `run.py` (según spec) | ✅ | ✅ (main_desktop llama) |

## 10. Respuestas a preguntas obligatorias de REALITY_MAP

### ¿Qué versión está realmente en ejecución?
Depende del método:
- `python run.py` → código **working tree** con 124 fixes sin commit
- EXE release/final (be1be8b0...) → código **working tree** al momento del build PyInstaller (desconocido cuándo)
- `uvicorn` → HEAD (sin fixes)
- `python desktop/main_desktop.py` → código **working tree** + _create_desktop_session()

### ¿Qué versión dicen los reportes que existe?
Los reportes (ROOT_CAUSE_REPORT, FINAL_STABILITY_REPORT, VALIDATION_REPORT) describen:
- Fixes de auth (bypass middleware) — existen solo en working tree
- Fix de onboarding (localStorage check) — existe solo en working tree
- Fix de sidebar, report detail — existen solo en working tree
- Fix de port 5173→8000 — SÍ existe en HEAD ✅
- SHA `4b49c23c` (FINAL_PACKAGE_AUDIT) — NO existe en ningún ZIP actual ❌

**Los reportes describen el working tree, no el HEAD de Git.**

### ¿Qué versión está en Git?
`40f34ba` — v1.4.0-rc2 — SOLO el fix de puerto 5173→8000. **Ningún otro fix está commiteado.**

### ¿Qué versión está en el EXE?
- EXE release/final (be1be8b0...): Build del working tree en momento desconocido
- EXE FINAL (744755c6...): Build distinto, 3× más grande, origen desconocido

**Ningún EXE coincide exactamente con lo que Git tiene en HEAD.**

### ¿Qué versión está en el ZIP?
5 ZIPs distintos, ninguno con SHA que coincida con reportes. Ninguno es reproducible desde el código actual.

---

## DIAGNÓSTICO

**El proyecto tiene al menos 3 "realidades":**

1. **Realidad Git (40f34ba)** — Solo fix de puerto. No refleja el estado real del producto.
2. **Realidad Working Tree** — Todos los fixes aplicados. Es lo que los reportes describen.
3. **Realidad EXE/ZIP** — Builds huérfanos sin trazabilidad a una revisión de código.

**Ninguna de las 3 realidades es reproducible externamente.**

## ACCIÓN REQUERIDA

Para que exista UNA SOLA REALIDAD verificable:

1. **Commit working tree completo** → Git refleja el código real del producto
2. **Eliminar ZIPs/EXEs redundantes** → Un solo ZIP oficial
3. **Rebuild desde commit limpio** → EXE reproducible desde Git
4. **Validar SHA** → Coincidencia perfecta entre ZIP, EXE, y working tree commiteado
