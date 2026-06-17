# PROJECT STATE — Rastro

**Versión:** 1.4.0-rc1
**Estado:** RELEASE CANDIDATE — lista para distribución
**Tests:** 159/159 pasando
**Build frontend:** 0 errores TS, ~1.7s
**Pipeline:** Target → Recon → Scoring → Hypothesis → Investigation → Validation → Evidence → Findings → Report

---

## Resumen

| Dimensión | Estado |
|-----------|--------|
| Backend | FastAPI + SQLAlchemy + SQLite/PostgreSQL, ~240 rutas, 51 routers |
| Frontend | React 19 + Vite 8 + TypeScript 6, 28 páginas |
| Desktop | pywebview 6 + pystray + auto-updater + PyInstaller |
| Mobile | Capacitor 8 scaffolded, APK build script |
| Tests | 159/159 (11 test files) |
| Auth | JWT + rate-limit + license HMAC-SHA256 |
| AI | Ollama + OpenAI-compatible + fallback local rule-based |
| PLE | 7 módulos + 12 endpoints + UI |
| i18n | Español default, EN/ES completos |
| WebSocket | Manager + bridge + router + client hook (activo en startup) |
| Notifications | Hub + bridges registrados (DB, desktop, email, FCM, WS) |

---

## Pipeline Core

```
Target → Recon (subfinder→httpx→katana→wayback)
       → Scoring (unified_scoring + classify)
       → Hypothesis (hypothesis engine)
       → Investigation (auto-creation + timeline + progress)
       → Validation (replayer→rules→confidence→gate)
       → Evidence (graph + store)
       → Findings (persisted + scored)
       → Report (CVSS + HackerOne/Bugcrowd/Markdown)
```

## Plataformas

| Plataforma | Estado | Distribución |
|------------|--------|-------------|
| Windows 10/11 | ✅ PyInstaller + NSIS | GitHub Releases |
| Linux x86_64 | ✅ PyInstaller + AppImage | Build script |
| Android | ✅ Capacitor scaffolded | `mobile/build_apk.sh` |
| macOS | ⚠️ Comunitario (no mantenido activamente) | `python run.py` |

## Documentación

| Documento | Estado |
|-----------|--------|
| README.md | ✅ Sincronizado |
| ARCHITECTURE.md | ✅ Sincronizado |
| ROADMAP.md | ✅ Sincronizado |
| OPENCODE_PLAN.md | ✅ Sincronizado |
| PROJECT_STATE.md | ✅ Este archivo |
| RELEASE_CHECKLIST.md | ✅ Ver abajo |
| INSTALL.md | ✅ Actualizado |
| MANUAL_ES.md | ✅ Actualizado |
| CHANGELOG.md | ✅ v1.0.0 → v1.3.0 |
| EVOLUTION_PLAN.md | ✅ Sincronizado |

## Licencia

Propietaria — HMAC-SHA256 con hardware fingerprint.

## Real-World Validation (2026-06-17)

**Target:** testphp.vulnweb.com (Acunetix test site)
**Result:** 9/9 pipeline stages passed

| Stage | Result |
|-------|--------|
| 1_create_target | ✅ Target created (ID 123) |
| 2_add_endpoints | ✅ 25/25 endpoints created |
| 3_hypotheses | ✅ 15 hypotheses (IDOR, PE, data exposure, GraphQL, auth bypass, SSRF) |
| 4_investigation | ✅ Investigation created from top hypothesis |
| 5_dashboard | ✅ Dashboard loaded (40% pipeline progress) |
| 6_report | ✅ Report generated (1 finding, $258k estimated value) |
| 7_export | ✅ 0 reports persisted (on-the-fly generation only) |
| 8_scoring | ✅ 15/25 endpoints have risk scores |
| 9_attack_surface | ✅ Attack surface loaded |

**Issues found:** None. All stages functional end-to-end.
**Missing:** No endpoint to delete targets (405 on DELETE). Reports are generated on-the-fly but not auto-persisted (expected behavior).

### Distribution artifacts
- `~/Desktop/Rastro-1.4.0-rc1-final-linux-x64.zip` — 89 MB (PyInstaller bundle + APK + docs)
- `dist/Rastro/Rastro` — 21 MB executable
- `dist/rastro-android-debug.apk` — 4.2 MB Android APK
