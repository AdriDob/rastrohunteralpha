# PROJECT STATUS — Rastro

**Versión actual:** v1.3.0  
**Fecha:** 2026-06-16  
**Estado general:** STABLE — pipeline integrado, Android scaffolded, sidebar con submenús  
**Sprint actual:** Estabilización v1.3.0 — pipeline unificado, UX, Android companion

---

## Progreso General

| Dimensión | Progreso | Estado |
|-----------|----------|--------|
| **Backend** | 96% | ✅ ~236 rutas, 44 routers, 17 tablas, 0 deprecation warnings |
| **Frontend** | 82% | ✅ 25 páginas, 0 errores TS, build ~1.4s |
| **Desktop** | 85% | ✅ pywebview, tray, auto-updater, 13-step boot |
| **Mobile** | 20% | ✅ Capacitor Android scaffolded, build script, mobile nav |
| **AI** | 72% | ✅ Ollama + OpenAI, PLE memory builder, AdaptivePrioritizer |
| **PLE** | 100% | ✅ Perfil, tracker, prioritizer, explainer, memory, export, UI |
| **i18n** | 92% | ✅ Español default, auto-detect, 22 nuevas claves PLE |
| **Auth** | 88% | ✅ JWT + User model + register/login/refresh + PBKDF2 |
| **Packaging** | 80% | ✅ PyInstaller, NSIS, AppImage, CI/CD |
| **Documentación** | 80% | ✅ Governance docs, docs sincronizados con código |
| **Testing** | 95% | ✅ 152 tests, 0 deprecation warnings propias |

---

## Próximos Objetivos (Sprint Actual)

1. ✅ PLE backend + frontend + tests (19 tests)
2. ✅ i18n upgrade (español default, auto-detect)
3. ✅ Governance docs (PROJECT_STATUS, TIMELINE, FEATURE_MATRIX, TECH_DEBT)
4. ✅ Docs sincronizados (docs stale archivados, VERSION→1.2.0)
5. ✅ WebSocket manager + event bus bridge + client hook (implementado en v1.3.0)
6. ⏳ Phase 3: Notification system (desktop push + email + FCM — bridges registrados, falta config)

---

## Blockers

| Blocker | Impacto | Plan |
|---------|---------|------|
| Windows cross-compilation vía wine en WSL2 | Medio | CI nativa via GitHub Actions; build local solo Linux |
| AppImage build local requiere FUSE | Bajo | Script creado, se ejecuta en Linux nativo |
| Chromium para Puppeteer no disponible en WSL2 | Bajo | Skipped — badges + demo flow en README suficientes |
| PostgreSQL pendiente de integración CI | Medio | Se añadirá cuando Phase 2 requiera DB central |

---

## Deuda Técnica

| Item | Prioridad | Notas |
|------|-----------|-------|
| `datetime.utcnow()` deprecado en 2 archivos | Baja | `gateway/schemas.py:25`, `learning/export.py:28` |
| StarletteDeprecationWarning testclient | Baja | `httpx` → `httpx2` cuando estable |
| 37 routers sin test unitarios individuales | Media | Cobertura actual solo via tests de integración |
| Sin test de base de datos PostgreSQL | Media | Depende de tener PostgreSQL en CI |
| Auto-migration ad-hoc en `db.py` | Baja | Funcional, pero sería mejor con Alembic |

---

## Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Scope creep en features | Alta | Alto | Strict phase gating, backlog priorizado |
| Rotura de compatibilidad SQLite↔PostgreSQL | Media | Alto | Dual DB support, migration script, tests |
| Frontend bundle size crece con i18n | Baja | Medio | Lazy loading de locales, tree-shaking |
| Mobile UI no se adapta bien | Media | Alto | Responsive refactor incremental, user testing |

---

## Decisiones Arquitectónicas Recientes

| Decisión | Opción | Razón |
|----------|--------|-------|
| **PLE storage** | Tabla SQLite (JSON fields) | Datos local-first, sin dependencias externas |
| **Password hashing** | PBKDF2-HMAC-SHA256 stdlib | Sin bcrypt; compatible con Django |
| **Idioma default** | Español | Experiencia nativa para mercado primario |
| **i18n engine** | React Context + archivos TS | Sin dependencias, tipado fuerte, tree-shakeable |
| **Session state** | sessionStorage | Persistencia por pestaña, sin cookies |
| **Docs stale** | Archive a `docs/archive/` | Historial preservado, docs activos reflejan código |
| **APP_VERSION** | Leer de VERSION file | Fuente única de verdad; elimina hardcode |
