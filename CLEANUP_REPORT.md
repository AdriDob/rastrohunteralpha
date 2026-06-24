# CLEANUP_REPORT.md

> Reporte de limpieza FASE 1 — Eliminación de ambigüedad y consolidación del repositorio.

---

## Resumen de acciones ejecutadas

| # | Acción | Estado |
|---|---|---|
| 1 | Evidencia de phantom directory recolectada (AUDIT_ARTIFACTS_REMOVED.md) | ✅ |
| 2 | Eliminación de phantom directory `C:\Users\...\rastro_build/` (537 MB, 366 archivos) | ✅ |
| 3 | Evidencia de `build/` recolectada (AUDIT_ARTIFACTS_REMOVED.md) | ✅ |
| 4 | Archivado de `build/` (128 MB, 32 archivos) a `archive/pre-consolidation/build/` | ✅ |
| 5 | Archivado de todos los ZIPs, APKs, EXEs subdirectorios y manifests de `dist/` a `archive/pre-consolidation/dist/` | ✅ |
| 6 | Limpieza completa de `dist/` (ahora vacío) | ✅ |
| 7 | Auditoría completa en REALITY_MAP.md | ✅ |

## Archivos generados

| Archivo | Propósito |
|---|---|
| `REALITY_MAP.md` | Mapeo completo de todas las versiones de realidad del proyecto |
| `AUDIT_ARTIFACTS_REMOVED.md` | Evidencia pre-eliminación de artifacts temporales |
| `CLEANUP_REPORT.md` | Este archivo — reporte de lo ejecutado |

## Estructura post-limpieza

```
proyecto/
├── archive/
│   └── pre-consolidation/
│       ├── build/        # build/ original (128 MB)
│       │   ├── Rastro/                  # PyInstaller Linux build
│       │   ├── main_desktop/            # Build alternativo (main_desktop.py)
│       │   ├── rastro/                  # Cache/directorio pequeño
│       │   ├── Rastro-1.5.0-stable.zip  # 2.8 MB
│       │   └── STABILITY_REPORT.md      # Reporte asociado
│       └── dist/         # dist/ original (~1 GB)
│           ├── Rastro/                          # PyInstaller Linux build
│           ├── Rastro-1.5.0-FINAL/              # Release FINAL (EXE + APK + Docs + Checksums)
│           ├── Rastro-1.5.0-stable/             # Release stable (EXE + APK + spec)
│           ├── android/                         # APK build output
│           ├── final/                           # Release final (Windows + Android + Docs + Checksums + Manifest)
│           ├── release/                         # Release individual (EXE + APK)
│           ├── Rastro-1.5.0-FINAL-DEFINITIVE-STABLE.zip
│           ├── Rastro-1.5.0-FINAL.zip
│           ├── Rastro-1.5.0-definitive.zip
│           ├── Rastro-1.5.0-stable.zip
│           ├── Rastro-Portable-1.5.0.zip
│           ├── rastro-android-debug.apk
│           ├── Rastro-1.5.0-checksums.sha256
│           ├── Rastro-1.5.0-manifest.json
│           ├── Rastro-1.5.0-stable-checksums.sha256
│           └── Rastro-1.5.0-stable-manifest.json
├── dist/                  # VACÍO — listo para rebuild oficial
├── REALITY_MAP.md         # Mapa de realidad
├── AUDIT_ARTIFACTS_REMOVED.md  # Evidencia de artifacts
└── CLEANUP_REPORT.md      # Este archivo
```

## Estado del workspace

| Componente | Estado |
|---|---|
| `dist/` | ✅ Vacío — listo para rebuild |
| `build/` | ✅ Archivado en `archive/pre-consolidation/build/` |
| Phantom `C:\...\` | ✅ Eliminado |
| `archive/pre-consolidation/` | ✅ Contiene todos los releases históricos como evidencia |

## Source of truth actual

| Elemento | Valor |
|---|---|
| HEAD Git | `40f34ba` — v1.4.0-rc2 (solo fix de puerto) |
| Working tree | 124 archivos modificados + 355 untracked (todos los fixes reales) |
| VERSION | `1.5.0` (solo en working tree, no en HEAD) |

## Próximo paso (FASE 2)

Consolidar el source of truth commiteando el working tree completo.

---

**Documento generado**: 2026-06-24
**Fase**: FASE 1 — Limpieza de ambigüedad
