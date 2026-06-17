# FINAL PACKAGE AUDIT — Rastro v1.4.0-rc1

**Fecha:** 2026-06-17
**ZIP:** `~/Desktop/Rastro-1.4.0-rc1-final-linux-x64.zip`
**SHA-256:** `11ace65b79ec9a71992ccf3ccef13a8f9848686b91fe55d78045d03aed8d5cc3`
**Tamaño:** 89.8 MB (94,196,731 bytes)
**Archivos:** 356

---

## 1. Contenido del paquete

| Ruta | Archivos | Tamaño | Descripción |
|------|----------|--------|-------------|
| `Rastro-Desktop/` | 346 | ~89.5 MB | Desktop Linux bundle (PyInstaller) |
| `Rastro-Desktop/run.sh` | 1 | 0.8 KB | Launcher script (bash) |
| `Rastro-Desktop/Rastro` | 1 | 21 MB | ELF 64-bit executable (PyInstaller) |
| `Rastro-Desktop/_internal/` | 344 | ~68 MB | Python 3.14 runtime + 34 packages + frontend_dist |
| `Rastro-Android/` | 1 | 4.2 MB | Android APK (Capacitor debug) |
| `Rastro-Android/rastro-android-debug.apk` | 1 | 4.2 MB | APK con 488 entries, classes.dex, AndroidManifest.xml |
| `Documentacion/` | 9 | ~42 KB | Documentación del proyecto |
| `VERSION` | 1 | 9 B | `1.4.0-rc1` |

## 2. Verificación por componente

### Desktop Linux
| Ítem | Estado | Evidencia |
|------|--------|-----------|
| Binary existe en ZIP | ✅ | `Rastro-Desktop/Rastro` (21 MB, ELF header `\x7fELF` confirmado) |
| run.sh existe | ✅ | Valid bash script con shebang, PATH, OLLAMA_HOST |
| Frontend embebido | ✅ | 48 archivos en `_internal/frontend_dist/`, incluye index.html |
| Dependencias incluidas | ✅ | Python 3.14 + numpy/scipy/PIL/cryptography/etc. |
| Autocontenido | ✅ | No requiere Python ni Node.js para ejecutar |
| **Leaked artifacts** | ✅ **CORREGIDO** | `database/rastro.db` y `logs/` eliminados del ZIP |

### Desktop Windows
| Ítem | Estado | Evidencia |
|------|--------|-----------|
| .exe en ZIP | ❌ **NO INCLUIDO** | No hay ningún archivo `.exe` en el ZIP |
| Instalador NSIS | ❌ **NO INCLUIDO** | No hay `.msi` en el ZIP |
| Script de build existe | ✅ | `scripts/build_windows.ps1` — requiere Windows + PowerShell 5.1 |
| Script de installer existe | ✅ | `installer/install_windows.nsi` — requiere NSIS 3.0+ |

**Conclusión Windows:** No hay build para Windows en este ZIP. El bundle es exclusivamente Linux. Para generar Windows se necesita:
1. Ejecutar `scripts/build_windows.ps1` en un entorno Windows (PowerShell 5.1+)
2. Compilar `installer/install_windows.nsi` con NSIS 3.0+
3. El proceso no está automatizado para CI multiplataforma

### Android APK
| Ítem | Estado | Evidencia |
|------|--------|-----------|
| APK en ZIP | ✅ | `Rastro-Android/rastro-android-debug.apk` |
| Tamaño | 4.2 MB | Compressed APK |
| Tipo | **DEBUG** | No contiene archivos .RSA/.DSA (firma release) |
| classes.dex | ✅ | Presente (código compilado) |
| AndroidManifest.xml | ✅ | Presente |
| resources.arsc | ✅ | Presente |
| Firma | ⚠️ **DEBUG** | Solo META-INF build metadata, sin certificado release |
| Instalable | ✅ | `adb install rastro-android-debug.apk` (requiere USB debugging) |

**Conclusión Android:** APK funcional pero DEBUG. No firmado para release. Instalable vía `adb install` o descarga directa con "Instalar desde orígenes desconocidos". Para release se necesita:
1. Keystore propio (`build_apk.sh --release`)
2. Firma con `jarsigner` o Android Studio
3. zipalign optimizado

### Documentación
| Documento | Estado | Observaciones |
|-----------|--------|---------------|
| README.md | ✅ | Sincronizado: 51 routers, ~240 routes, 159 tests, 1GB RAM min |
| ARCHITECTURE.md | ✅ | Sincronizado: ~240 rutas, 51 routers |
| CHANGELOG.md | ✅ | v1.4.0-rc1 actualizado |
| GUIA_RAPIDA.md | ✅ | Incluye ZIP bundle + source instructions |
| MANUAL_ES.md | ✅ | Incluye ZIP bundle + source instructions |
| PROJECT_STATE.md | ✅ | Sincronizado: 159 tests, ~240 rutas |
| RELEASE_CHECKLIST.md | ✅ | Sincronizado: 159/159 tests |
| REAL_WORLD_VALIDATION.md | ✅ | 9/9 stages, testphp.vulnweb.com |
| RELEASE_NOTES.md | ✅ | Capacidades, limitaciones, requisitos, flujo |

**No hay referencias obsoletas** — se verificó que README.md no contiene "236 routes", "44 routers", "122 tests", "512 MB".

### Scripts
| Script | Estado | Descripción |
|--------|--------|-------------|
| `Rastro-Desktop/run.sh` | ✅ | Launcher: setea PATH, OLLAMA_HOST, RASTRO_DESKTOP=1 |
| `Rastro-Desktop/_internal/uninstall_windows.ps1` | ⚠️ Solo Windows | No ejecutable en Linux |

### Dependencias necesarias

**Para el Desktop Linux (ZIP):**
| Dependencia | Tipo | Nota |
|-------------|------|------|
| Linux x86_64 (glibc 2.35+) | Sistema | Requerido para ELF binary |
| RAM 1 GB mínimo, 4 GB recomendado | Sistema | OpenBLAS + Python runtime |
| subfinder/httpx/katana/waybackurls | Opcional | Go binaries en `~/go/bin` para recon |
| Ollama | Opcional | Para AI Conversacional |

**Para Android APK:**
| Dependencia | Tipo | Nota |
|-------------|------|------|
| Android 8+ (API 26+) | Dispositivo | Para instalar APK |
| USB Debugging o "Instalar APK" | Configuración | Para debug APK sin Play Store |

---

## 3. Integridad del ZIP

| Check | Resultado |
|-------|-----------|
| Archivos faltantes (vs esperados) | ✅ Ninguno — 9 docs + binary + APK + run.sh + _internal |
| Archivos duplicados (contenido real) | ✅ Falsos positivos — `.so` duplicados en distintas rutas de empaquetado, es normal en PyInstaller |
| Rutas rotas | ✅ No hay symlinks ni rutas absolutas |
| Recursos ausentes | ✅ Frontend completo (48 archivos en frontend_dist), CA cert bundle presente |
| Scripts inválidos | ✅ `run.sh` tiene shebang válido, sintaxis bash correcta |
| Artifacts de desarrollo | ✅ **CORREGIDO** — database/ y logs/ eliminados |
| VERSION consistente | ✅ `VERSION` = `1.4.0-rc1` = `_internal/VERSION` |
| Binary ELF válido | ✅ Header `\x7fELF` confirmado |

---

## 4. Problemas encontrados y acciones

### ❌ Crítico: No hay build Windows
- **Problema:** El ZIP solo contiene Linux bundle. Windows no está soportado en este release.
- **Acción necesaria:** Documentar en RELEASE_NOTES.md — YA ESTÁ DOCUMENTADO.

### ⚠️ Limitación: APK no firmado para release
- **Problema:** El APK es debug, requiere USB debugging o "orígenes desconocidos".
- **Acción necesaria:** Documentar en RELEASE_NOTES.md — YA ESTÁ DOCUMENTADO.

### ✅ Corregido: Leaked runtime artifacts
- **Problema:** `database/rastro.db` y `logs/` del entorno dev estaban en el ZIP.
- **Acción:** Eliminados de `dist/Rastro/` y ZIP recreado.

### ℹ️ Observación: Dependencias externas no incluidas
- **Problema:** subfinder, httpx, katana, waybackurls no vienen en el bundle.
- **Acción:** Documentado en RELEASE_NOTES.md y MANUAL_ES.md como requisito opcional.
- **Nota:** Es esperado — son Go binaries de terceros, no redistribuibles en el bundle.

---

## 5. Tabla resumen

| Componente | Estado | Observaciones |
|------------|--------|---------------|
| **Desktop Linux** | ✅ Listo | Bundle PyInstaller 21 MB + run.sh, autocontenido, 340+ deps empaquetadas |
| **Desktop Windows** | ❌ No incluido | Scripts existen pero requieren entorno Windows para build. No hay .exe ni instalador en el ZIP |
| **Android APK** | ⚠️ Debug only | APK 4.2 MB funcional vía adb, sin firma release, no publicable en Play Store |
| **Documentación** | ✅ Completa | 9 documentos sincronizados con estado actual del proyecto, sin referencias obsoletas |
| **Scripts** | ✅ Funcional | `run.sh` válido con shebang, path discovery, OLLAMA_HOST configurable |
| **Dependencias** | ✅ Incluidas (Linux) | Python 3.14 + 34 packages en _internal/. Go/Ollama no incluidos (documentado) |
| **Integridad ZIP** | ✅ Consistente | 356 archivos, sin leaks, sin rutas rotas, VERSION consistente, ELF válido |
| **Oportunidades** | 26 activas (API) | Documentado como 26 en RELEASE_NOTES.md |

---

## 6. Veredicto final

El paquete `Rastro-1.4.0-rc1-final-linux-x64.zip` está **completo y consistente para Linux x86_64**.

Limitaciones conocidas (todas documentadas):
- ❌ Windows no incluido en este ZIP
- ⚠️ Android APK debug (no release)
- ⚠️ Herramientas Go (subfinder, etc.) no incluidas
- ⚠️ Ollama requerido para AI (opcional para pipeline core)

**El ZIP está listo para distribución como Release Candidate Linux.**
