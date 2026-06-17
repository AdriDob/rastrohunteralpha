# TECH DEBT — Rastro

Registro de deuda técnica, legacy, duplicaciones, mejoras pendientes y refactors necesarios.

---

## 🔴 Alta Prioridad

| Item | Archivo | Descripción | Propuesta |
|------|---------|-------------|-----------|
| Sin tests unitarios por router | `api/routers/*` (37 routers) | Solo tests de integración, no unitarios | Agregar tests unitarios con mocks para cada router |
| Sin CI PostgreSQL | `.github/workflows/` | Tests solo en SQLite; PostgreSQL no se prueba | Añadir service PostgreSQL en CI workflow |
| Auto-migration ad-hoc en init_db | `database/db.py` | ALTER TABLE manual para targets_intel | Migrar a Alembic cuando PostgreSQL sea primario |
| No hay type checking en runtime | `frontend/` | fetchJson devuelve `any`, muchos casts | Agregar validación con Zod en capa API |

---

## 🟡 Media Prioridad

| Item | Archivo | Descripción | Propuesta |
|------|---------|-------------|-----------|
| StarletteDeprecationWarning testclient | `tests/*` | Usa `httpx`, requiere `httpx2` | Migrar cuando httpx2 sea estable (external dep)
| Sin tests para desktop modules | `desktop/*` | Cobertura 0% en módulos desktop | Agregar tests con mocks de pywebview |
| Seed data sin documentar | `scripts/seed.py` | Datos de ejemplo no documentados | Documentar schema de seed data |
| DTO normalizer duplicado | `frontend/src/lib/api/adapter.ts` | Normalizer separado de api.ts | Evaluar si es necesario o unificar |

---

## 🟢 Baja Prioridad

| Item | Archivo | Descripción | Propuesta |
|------|---------|-------------|-----------|
| No hay lazy loading para locales | `frontend/src/lib/i18n*.ts` | Todos los locales se importan al inicio | Code-split locales con `import()` dinámico |
| Estilos inline generalizados | `frontend/src/pages/*` | Sin CSS modules, todo en inline styles | Refactor opcional cuando haya design system |
| Mobile responsive incompleto | `frontend/src/pages/*` | Muchas páginas usan isMobile solo para padding | Revisión completa responsive |
| Sin healthcheck en docker-compose | — | No hay docker-compose.yml | Crear docker-compose para PostgreSQL + API |
| Sin documentación de API endpoints | — | No hay OpenAPI/Swagger más allá del generado | Agregar descripciones a routers y schemas |
| VERSION file vs package.json | `VERSION` (1.0.0) vs frontend | Frontend no lee VERSION | Sincronizar o centralizar |

---

## ♻️ Refactors Propuestos

| Refactor | Área | Beneficio | Esfuerzo |
|----------|------|-----------|----------|
| Extraer AuthService de middleware | Auth | Testeable, reutilizable | 2 días |
| Unificar manejo de sesiones DB | Database | Eliminar código duplicado en 37 routers | 3 días |
| Migrar a Pydantic v2 settings | Config | Tipado fuerte, validación automática | 1 día |
| Separar frontend en chunks por ruta | Frontend | Bundle splitting más fino | 2 días |
| Crear API client tipado con Zod | Frontend | Eliminar `any`, errores en compile-time | 3 días |

---

## 📊 Estadísticas

| Métrica | Valor |
|---------|-------|
| Total de archivos .py | ~150 |
| Total de archivos .ts/.tsx | ~60 |
| Líneas de código backend | ~25,000 |
| Líneas de código frontend | ~15,000 |
| Tests | 152 |
| Cobertura de tests (estimada) | ~40% |
| Dependencias Python | ~30 |
| Dependencias Node | ~15 |
| Issues conocidos | ~15 |
| FIXME/TODO en código | ~8 |
