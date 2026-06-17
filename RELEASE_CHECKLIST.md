# RELEASE CHECKLIST — Rastro

## Pre-Release

### Tests
- [ ] `pytest tests/ -q --tb=short` → 159/159 passed
- [ ] `cd frontend && npm run build` → 0 errores TS, build exitoso
- [ ] `python scripts/prebuild.py` → todas las fases verdes

### Documentación
- [ ] README badges con versión correcta
- [ ] ARCHITECTURE.md sincronizado (routers, rutas, páginas)
- [ ] CHANGELOG.md actualizado con cambios del release
- [ ] INSTALL.md actualizado
- [ ] MANUAL_ES.md actualizado
- [ ] VERSION file actualizado

### Pipeline
- [ ] Target → Recon: crear target, lanzar scan, ver endpoints
- [ ] Scoring: endpoints tienen scores
- [ ] Hypothesis: correr hypothesis engine
- [ ] Investigation: promover hipótesis, ver timeline
- [ ] Validation: replayer + rules + confidence
- [ ] Evidence: graph + store funcional
- [ ] Verdict + Report: generar y exportar reporte

### Desktop
- [ ] Windows build: `scripts/build_windows.ps1`
- [ ] Linux build: `scripts/build_linux.sh`
- [ ] AppImage build: `scripts/build_appimage.sh`
- [ ] NSIS installer funciona
- [ ] Auto-updater verificado

### Android
- [ ] `mobile/build_apk.sh` → APK generado
- [ ] APK instalable en dispositivo/emulador
- [ ] Login funcional en mobile
- [ ] Navegación básica funcional

## Release

- [ ] Tag creado: `git tag vX.Y.Z`
- [ ] GitHub Release creado con binarios adjuntos
- [ ] CI/CD release workflow exitoso
- [ ] Changelog publicado en Release notes

## Post-Release

- [ ] README badges actualizados a nueva versión
- [ ] CHANGELOG preparado para próximo release
- [ ] PROJECT_STATE.md actualizado
