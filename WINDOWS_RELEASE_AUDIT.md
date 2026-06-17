# WINDOWS RELEASE AUDIT — Rastro v1.4.0-rc1

**Fecha:** 2026-06-17
**Auditor:** Automatizada (verificación CI + local)

---

## 1. Windows Build

| Ítem | Estado | Evidencia |
|------|--------|-----------|
| Ejecutable (.exe) | ✅ **EXISTE Y ES VÁLIDO** | `Rastro.exe` (16 MB) — PE32 header `MZ` + `PE\0\0` confirmados |
| Instalador (.msi / .exe installer) | ❌ **No incluido** | CI produce solo PyInstaller directory build; NSIS no se ejecuta en CI |
| Frontend embebido | ✅ | 50 archivos en `_internal/frontend_dist/`, incluye index.html |
| Dependencias incluidas | ✅ | Python 3.12 + 161 DLLs + packages empaquetados |
| VERSION | ✅ | `1.4.0-rc1` (consistente root + _internal) |
| Artifacts de desarrollo | ✅ **No leaks** | Sin database/rastro.db ni logs/ |
| Origen | ✅ GitHub Actions | Build realizado en `windows-latest` vía CI workflow |

### Detalles del build Windows
- **Plataforma:** Windows (x86_64) — `windows-latest` GitHub Actions runner
- **Python:** 3.12 (según CI workflow)
- **PyInstaller:** Build directory (no one-file), output `dist/Rastro/Rastro.exe`
- **Entrypoint:** `run.py` → `desktop/main_desktop.py` → FastAPI + pywebview
- **Frontend:** Build desde source (Vite 8, React 19, TypeScript 6)
- **Instalador:** No se genera en CI — el NSIS installer (`installer/install_windows.nsi`) requiere ejecución manual en Windows

### Cómo generar Windows localmente
```powershell
# En un entorno Windows con PowerShell 5.1+
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
cd frontend
npm ci
npm run build
cd ..
pyinstaller Rastro.spec -y
# Opcional: compilar instalador NSIS
makensis installer\install_windows.nsi
```

---

## 2. Android APK

| Ítem | Estado | Evidencia |
|------|--------|-----------|
| APK en ZIP | ✅ | `Rastro-Android/rastro-android-debug.apk` (4.2 MB) |
| Tipo | ⚠️ **DEBUG** | Sin firma release (no .RSA/.DSA) |
| classes.dex | ✅ | Presente (488 entries total en APK) |
| AndroidManifest.xml | ✅ | Presente |
| Instalable | ✅ | Vía `adb install` o "Instalar desde orígenes desconocidos" |

---

## 3. Paquete unificado

**Archivo:** `~/Desktop/Rastro-1.4.0-rc1-final-unified.zip`
**Tamaño:** 140 MB
**Archivos:** 1,427

| Componente | Files | Tamaño | Descripción |
|------------|-------|--------|-------------|
| `Rastro-Windows/` | 1,070 | ~52 MB | `Rastro.exe` (16 MB) + 161 DLLs + frontend + Python 3.12 |
| `Rastro-Linux/` | 345 | ~84 MB | `Rastro` (21 MB ELF) + `run.sh` + .so libs + frontend + Python 3.14 |
| `Rastro-Android/` | 1 | 4.2 MB | `rastro-android-debug.apk` |
| `Documentacion/` | 10 | ~55 KB | README, ARCHITECTURE, CHANGELOG, GUIA_RAPIDA, MANUAL_ES, PROJECT_STATE, RELEASE_CHECKLIST, REAL_WORLD_VALIDATION, RELEASE_NOTES, FINAL_PACKAGE_AUDIT |
| `VERSION` | 1 | 9 B | `1.4.0-rc1` |

---

## 4. Verificaciones de integridad

| Check | Resultado |
|-------|-----------|
| Windows .exe válido | ✅ PE header `MZ` + `PE\0\0` |
| Linux ELF válido | ✅ ELF header `\x7fELF` |
| APK válido | ✅ ZIP header `PK`, classes.dex presente |
| Frontend presente (Win) | ✅ 50 archivos, index.html |
| Frontend presente (Linux) | ✅ 48 archivos, index.html |
| VERSION consistente | ✅ `1.4.0-rc1` en todas las copias |
| Leaked artifacts | ✅ Ninguno (sin database/ o logs/) |
| Documentación completa | ✅ 10 archivos, ninguno faltante |
| Dependencias Windows | ✅ 161 DLLs empaquetadas |
| Dependencias Linux | ✅ 91 .so empaquetadas |

---

## 5. Limitaciones conocidas

### Windows
1. **Sin instalador NSIS**: No se genera en CI. El `Rastro.exe` debe ejecutarse desde `Rastro-Windows/`.
2. **Sin acceso directo**: No crea atajo en escritorio ni menú inicio.
3. **Antivirus**: PyInstaller executables suelen generar falsos positivos en Windows Defender.
4. **Python 3.12**: Build en CI usa 3.12 (no 3.14 como Linux). El spec `Rastro.spec` excluye scipy/matplotlib para reducir tamaño.

### Android
1. **Debug APK**: No firmado para release. No publicable en Play Store.
2. **Companion**: Requiere desktop/API corriendo en la red. No es autónomo.
3. **Requiere USB debugging o "orígenes desconocidos"** para instalación.

### General
1. **Herramientas Go**: subfinder/httpx/katana/waybackurls no incluidas en ningún bundle.
2. **Ollama**: Requerido para AI Conversacional (opcional para pipeline core).

---

## 6. Veredicto

| Componente | Estado | Acción requerida |
|------------|--------|------------------|
| **Windows** | ✅ Build válido verificado | Subir como artifact del release |
| **Linux** | ✅ Build válido verificado | Incluido en paquete unificado |
| **Android** | ⚠️ Debug APK | Incluido, documentado como debug |
| **Documentación** | ✅ Completa y sincronizada | Incluida en paquete |
| **Paquete unificado** | ✅ 140 MB, 1,427 archivos, sin leaks | Listo para distribución |

**El release v1.4.0-rc1 está completo para Windows (x86_64), Linux (x86_64) y Android (debug).**
