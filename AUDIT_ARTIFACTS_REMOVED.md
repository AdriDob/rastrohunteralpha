# AUDIT_ARTIFACTS_REMOVED.md

> Evidencia de artefactos temporales y de build eliminados del repositorio.
> Generado antes de cualquier eliminación. Sirve como registro de auditoría.

---

## 1. Directorio fantasma: `C:\Users\adrie\AppData\Local\Temp\rastro_build/`

### Detalles

| Campo | Valor |
|---|---|
| Ruta real en Linux | `./C:\Users\adrie\AppData\Local\Temp\rastro_build/` |
| Tamaño total | 537 MB |
| Archivos totales | 366 |
| Fecha creación | 2026-06-24 03:39:16 |
| Última modificación | 2026-06-24 03:39:42 |

### Contenido

```
Rastro.spec        # 3.7K, spec de PyInstaller (Jun 13)
run.py              # 1.8K, entrypoint (Jun 13)
ai/                 # 3 archivos (analysis.py, ollama_client.py, __init__.py)
api/                # Múltiples archivos (main.py, scheduler.py, routers/, middleware/, schemas/)
core_engines/       # 41 subdirectorios, archivos de engine completos
database/           # Archivos de base de datos
desktop/            # main_desktop.py y relacionados
frontend/           # Frontend (posiblemente build)
```

### Origen

Build de PyInstaller ejecutado desde WSL2 que utilizó `C:\Users\...` como temp directory de Windows. El path literal de Windows fue creado como directorio en Linux en lugar de usar `/tmp/`. Esto contaminó el workspace con 537 MB de código duplicado.

### Archivos duplicados confirmados

Todo el contenido del directorio fantasma es una copia del source tree (`run.py`, `api/`, `core_engines/`, `desktop/`, `frontend/`, `ai/`, `database/`). Ningún archivo es único. La copia del source data del 13 de Jun (spec) al 24 de Jun (frontend), indicando que fue creado en múltiples sesiones de build.

### Motivo de eliminación

1. **Contaminación del workspace**: Interfiere con búsquedas (`grep`, `find`), globs y operaciones de git.
2. **Duplicación**: 100% del contenido ya existe en el source tree real.
3. **Sin valor histórico**: No es un release, no tiene metadatos de build, no es reproducible.
4. **Tamaño**: 537 MB de espacio desperdiciado.

---

## 2. Directorio `build/`

### Detalles

| Campo | Valor |
|---|---|
| Ruta | `build/` |
| Tamaño total | 128 MB |
| Archivos totales | 32 |
| Fecha creación | 2026-06-10 22:51 |
| Última modificación | 2026-06-20 18:46 |

### Contenido

```
build/Rastro-1.5.0-stable.zip          # 2.8 MB
build/STABILITY_REPORT.md              # 7.8 KB, reporte de estabilidad
build/Rastro/                          # PyInstaller Linux build output
  └── _internal/                       # Dependencias congeladas (.pyc)
build/main_desktop/                    # Build alternativo (entrypoint main_desktop.py)
build/rastro/                          # Directorio pequeño (probablemente cache)
```

### Motivo de eliminación

1. **Artefacto temporal de PyInstaller**: El directorio `build/` es generado automáticamente por PyInstaller durante el proceso de empaquetado. No debe formar parte del repositorio.
2. **Duplicación**: El ZIP y el binario Linux dentro de `build/` son artifacts de compilación que no reflejan el estado actual del código.
3. **Sin trazabilidad**: No hay registro de qué commit produjo estos artifacts.
4. **128 MB de espacio desperdiciado** que debe ser reconstruible desde el source.

---

## Resumen de espacio recuperado

| Artefacto | Archivos | Tamaño |
|---|---|---|
| Phantom C:\ | 366 | 537 MB |
| build/ | 32 | 128 MB |
| **Total** | **398** | **665 MB** |

---

## Checksums pre-eliminación

### Phantom directory (archivos clave)

```
sha256sum "C:\Users\adrie\AppData\Local\Temp\rastro_build/run.py"
sha256sum "C:\Users\adrie\AppData\Local\Temp\rastro_build/Rastro.spec"
```

### build/

```
de0de14a338476b373a7e60536858a7be6041579276732bef1e0759fc13a0cfa  build/Rastro-1.5.0-stable.zip
```

---

**Documento generado**: 2026-06-24
**Fase**: FASE 1 — Limpieza de ambigüedad
