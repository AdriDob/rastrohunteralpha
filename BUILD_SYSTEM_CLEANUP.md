# BUILD_SYSTEM_CLEANUP.md

> Correcciones realizadas al sistema de build durante la FASE 3 de consolidación.

---

## Script auditados

| Script | Entrypoint | ¿Correcto? | Estado |
|---|---|---|---|
| `Rastro.spec` | `run.py` | ✅ | Correcto — referencia oficial |
| `scripts/build_windows_v15.ps1` | `Rastro.spec` → `run.py` | ✅ | Recomendado para Windows |
| `scripts/build_windows.ps1` | `Rastro.spec` → `run.py` | ✅ | Correcto |
| `scripts/build.ps1` | `Rastro.spec` → `run.py` | ✅ | Correcto (obsoleto, v1.0.0-rc1) |
| `scripts/build_android.py` | Capacitor + Gradle | ✅ | Pipeline separado (no usa PyInstaller) |
| `scripts/build_release.py` | `launcher.py` | ⚠️ | No usa PyInstaller; copia fuente. Legacy. |
| `scripts/package_definitive_release.py` | N/A (packaging) | ✅ | Solo empaqueta artifacts existentes |
| `scripts/package_v15_definitive.py` | N/A (packaging) | ✅ | Solo empaqueta artifacts existentes |
| `scripts/package_portable.py` | N/A (packaging) | ✅ | Solo empaqueta artifacts existentes |

## Corrección aplicada

### `scripts/build_windows_exe.py`

**Problema**: Línea 109 usaba `desktop/main_desktop.py` como entrypoint de PyInstaller, bypassando `run.py` que contiene `_ensure_frontend_build()` y path bootstrap.

**Corrección**: Cambiado a `run.py`:

```python
# Antes (line 109):
r'{WIN_TEMP}\\desktop\\main_desktop.py',

# Después (line 109):
r'{WIN_TEMP}\\run.py',
```

**Impacto**: El EXE generado ahora ejecuta `run.py` → `_ensure_frontend_build()` → `desktop.main_desktop.main()`, igual que el spec oficial.

## Scripts redundantes identificados

| Script | Razón | Recomendación |
|---|---|---|
| `scripts/build.ps1` | Hardcoded v1.0.0-rc1, ruta WSL específica | Mantener como histórico |
| `scripts/build_release.py` | No produce EXE funcional; solo copia fuente | Mantener como histórico |
| `scripts/package_v15_definitive.py` | Depende de `WINDOWS_ZIP` fijo (Rastro-1.4.0-rc2) | Mantener como histórico |

## Pipeline oficial post-corrección

```
┌─────────────────────────────────────────────────────┐
│                   BUILD PIPELINE                     │
├─────────────────────────────────────────────────────┤
│  1. python scripts/build_frontend.sh                 │
│     → Produce frontend/dist/                         │
│                                                      │
│  2. pyinstaller Rastro.spec -y                       │
│     → run.py como entrypoint                         │
│     → Produce dist/Rastro/Rastro.exe                 │
│                                                      │
│  3. scripts/build_windows_v15.ps1 (opcional)         │
│     → Wrapper que ejecuta paso 2 + crea ZIP          │
│                                                      │
│  4. python scripts/package_portable.py               │
│     → Empaqueta dist/Rastro/ en ZIP portable         │
└─────────────────────────────────────────────────────┘
```

---

**Documento generado**: 2026-06-24
**Fase**: FASE 3 — Fix crítico de build system
