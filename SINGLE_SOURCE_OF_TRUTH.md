# SINGLE_SOURCE_OF_TRUTH.md

> Definición explícita del Source of Truth oficial del proyecto Rastro 1.5.0.

---

## 1. Entrypoint oficial

**`run.py`** en la raíz del repositorio.

Flujo de ejecución:

```
run.py
  ├── _ensure_frontend_build()   → Build frontend si no existe dist/
  ├── desktop.main_desktop.main()
       ├── _create_desktop_session() → WebView/CEF window
       ├── uvicorn api.main:app      → Backend API server
       └── Browser fallback          → Si WebView no disponible
```

**PROHIBIDO**:
- Usar `desktop/main_desktop.py` como entrypoint de build PyInstaller ❌
- Usar `uvicorn api.main:app` standalone para releases ❌
- Usar `python desktop/main_desktop.py` directamente para producción ❌

## 2. Build pipeline oficial

### 2.1 Prerrequisitos

```
Python 3.12+ con PyInstaller 6.20+
Node.js 20+ con npm
```

### 2.2 Frontend

```bash
cd frontend
npm ci          # Instalar dependencias
npm run build   # Build producción → frontend/dist/
```

### 2.3 Desktop (Windows/Linux)

```bash
# Método 1: Directo (recomendado)
pyinstaller Rastro.spec -y
# → Produce: dist/Rastro/Rastro.exe (Windows)
# → Produce: dist/Rastro/Rastro     (Linux)

# Método 2: PowerShell wrapper (Windows)
.\scripts\build_windows_v15.ps1
# → Ejecuta pyinstaller Rastro.spec -y + crea ZIP
```

### 2.4 Android

```bash
python scripts/build_android.py
# → Produce: dist/android/Rastro-debug.apk
```

### 2.5 Packaging

```bash
python scripts/package_portable.py
# → Produce: dist/Rastro-Portable-{version}.zip
```

## 3. Versión

La versión oficial se lee del archivo `VERSION` en la raíz.

Actual: **1.5.0**

## 4. Commits que definen v1.5.0

| Hash | Fecha | Descripción |
|---|---|---|
| `561d11e` | 2026-06-24 | v1.5.0: apply all working tree fixes |
| `4a97943` | 2026-06-24 | v1.5.0: add new modules |
| `fadc002` | 2026-06-24 | v1.5.0: add audit reports and documentation |

## 5. Archivos que NO deben tocarse manualmente

| Archivo | Propósito |
|---|---|
| `run.py` | Entrypoint único — no cambiar sin revisión de arquitectura |
| `Rastro.spec` | Configuración oficial de PyInstaller |
| `VERSION` | Versión del release |
| `api/main.py` | Aplicación FastAPI |
| `desktop/main_desktop.py` | Sesión desktop (llamado DESDE run.py) |

## 6. Reglas de oro

1. **TODO build debe ser reproducible desde `git clone` + `pyinstaller Rastro.spec -y`**
2. **Ningún script de build debe usar `main_desktop.py` como entrypoint directo**
3. **El frontend se build dead dentro del pipeline, no se incluye en git**
4. **Los ZIPs de release se generan desde `dist/`, no se commitean**
5. **La version se lee de `VERSION`, no de hardcode en scripts**
6. **Si un script no usa `Rastro.spec`, debe justificarse explícitamente**

---

**Documento generado**: 2026-06-24
**Fase**: FASE 2 — Consolidación del Source of Truth
