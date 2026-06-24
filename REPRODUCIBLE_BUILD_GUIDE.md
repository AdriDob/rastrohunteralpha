# REPRODUCIBLE_BUILD_GUIDE.md

> Guía paso a paso para reproducir el build de Rastro 1.5.0 desde cero.

---

## Prerrequisitos

| Herramienta | Versión | Verificación |
|---|---|---|
| Git | ≥ 2.30 | `git --version` |
| Python | ≥ 3.12 | `python --version` |
| PyInstaller | ≥ 6.20 | `pyinstaller --version` |
| Node.js | ≥ 20 | `node --version` |
| npm | ≥ 9 | `npm --version` |
| JDK | ≥ 17 (solo Android) | `java --version` |
| Android SDK | API 35 (solo Android) | `echo $ANDROID_HOME` |

## Procedimiento

### 1. Clonar el repositorio

```bash
git clone <repo-url> rastro
cd rastro
git checkout main
```

### 2. Verificar el commit

```bash
git log --oneline -1
# Debe mostrar: 1f13569 v1.5.0: add build system cleanup and source of truth docs
# O posterior (v1.5.0 consolidado)

cat VERSION
# Debe mostrar: 1.5.0
```

### 3. Instalar dependencias Python

```bash
pip install -r requirements.txt
pip install pyinstaller
```

### 4. Build frontend

```bash
cd frontend
npm ci
npm run build
cd ..
```

Verificar que existe:

```bash
ls frontend/dist/index.html
```

### 5. Build desktop (PyInstaller)

```bash
pyinstaller Rastro.spec -y
```

El spec usa `run.py` como entrypoint. Flujo:

```
Rastro.spec → run.py → _ensure_frontend_build() → desktop.main_desktop.main()
```

### 6. Verificar output

```bash
ls -la dist/Rastro/
# Debe contener:
#   Rastro.exe (Windows) o Rastro (Linux)
#   _internal/ (dependencias congeladas)
```

```bash
# Windows
sha256sum dist/Rastro/Rastro.exe

# Linux
sha256sum dist/Rastro/Rastro
```

### 7. (Opcional) Crear ZIP portable

```bash
python scripts/package_portable.py --source dist/Rastro --output dist --version 1.5.0
# Produce: dist/Rastro-Portable-1.5.0.zip
```

### 8. (Opcional) Build Android APK

```bash
python scripts/build_android.py
# Produce: dist/android/Rastro-debug.apk
```

## Verificación de consistencia

Después del build, verificar:

```bash
# 1. Entrypoint correcto
grep "run.py" Rastro.spec
# Debe mostrar: ['run.py'],

# 2. Versión correcta
cat VERSION
# Debe mostrar: 1.5.0

# 3. Frontend build existe
test -f frontend/dist/index.html && echo "OK"

# 4. No hay builds alternativos en dist/
ls dist/*.zip 2>/dev/null && echo "WARNING: stale ZIPs detected" || echo "OK: no stale ZIPs"

# 5. No hay builds previos no commiteados
git status --short
# Debe estar limpio
```

## SHA256 esperados (cuando se genere desde este commit)

> Los SHA varían según plataforma y versión de dependencias.
> El SHA oficial se genera durante el build y se documenta en el ZIP/checksums.

## Troubleshooting

### "Frontend dist not found"

Asegúrate de haber ejecutado `npm run build` en `frontend/`.

### PyInstaller missing modules

Si PyInstaller reporta módulos faltantes, verificar:

```bash
pip install -r requirements.txt
```

### Error: `desktop.main_desktop` not found

Verifica que `run.py` está en el PATHEX. El spec ya incluye `pathex=[PROJECT_ROOT]`.

### Error en Android build

Asegurar:

```bash
export ANDROID_HOME=~/Android/Sdk  # o donde esté instalado
npx cap sync android               # Sincronizar Capacitor
```

## Principio de reproducibilidad

```bash
# Build completo desde cero (Linux/macOS):
git clone <url> rastro && cd rastro && \
pip install -r requirements.txt && pip install pyinstaller && \
cd frontend && npm ci && npm run build && cd .. && \
pyinstaller Rastro.spec -y && \
echo "Build reproducible: dist/Rastro/Rastro ready"
```

Si este procedimiento no produce un EXE funcional idéntico al release oficial, el build NO es reproducible — reportar como bug de release engineering.

---

**Documento generado**: 2026-06-24
**Fase**: FASE 3 — Fix crítico de build system
