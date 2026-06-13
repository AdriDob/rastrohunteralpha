# Rastro — Inteligencia de Superficie de Ataque

Sistema semi-autónomo de recon y priorización para bug bounty.
Motor de inteligencia centralizado con scoring determinista, reducción de ruido
y reportes basados en snapshots.

## ¿Qué es Rastro?

Rastro es una herramienta local-first para cazadores de bugs que necesitan:

- Descubrir y catalogar endpoints de alto valor (APIs, GraphQL, paneles admin, multi-tenant)
- Puntuar objetivos con heurísticas deterministas (sin ML)
- Validar hallazgos con un pipeline de verificación
- Tener todo corriendo localmente, sin depender de servicios cloud

## Estado actual

**Backend**: ✅ Funcional (15/15 endpoints críticos → HTTP 200, 0 endpoints con 500)
**Frontend**: ✅ Compila (Vite + React, ~1s build)
**Base de datos**: ✅ SQLite con datos seed (5 targets, 50 endpoints, 8 findings, 54 verdicts, 5 targets_intel)
**Oportunidades**: ✅ ~48 oportunidades auto-descubiertas en startup vía 5 providers
**Stats**: ✅ Nuevo endpoint `/api/stats` con conteos en tiempo real
**Desktop**: ✅ Build configurado para Windows 11 (PyInstaller)

## Requisitos

| Dependencia | Requerido | Notas |
|-------------|-----------|-------|
| Python 3.10+ | Sí | |  Actualizaremos
| FastAPI / Uvicorn | Sí | Backend |
| SQLAlchemy | Sí | ORM |
| Node.js 18+ | Para frontend | Build de producción |
| subfinder | Opcional | Descubrimiento de subdominios |
| httpx | Opcional | HTTP probing |
| katana | Opcional | NO INSTALADO actualmente |
| Ollama | Opcional | Resúmenes AI |

## Cómo arrancar (desarrollo)

```bash
# Backend
cd /home/adrie/projects/Rastro
source .venv/bin/activate
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# Frontend (otra terminal)
cd frontend
npm run dev

# O todo junto (desktop mode)
python desktop/main_desktop.py --dev
```

### URLs

| Servicio | URL |
|----------|-----|
| API | http://127.0.0.1:8000 |
| Frontend (dev) | http://localhost:5173 |
| Health check | http://127.0.0.1:8000/api/health |

## Cómo hacer el build para Windows

```bash
# 1. Compilar frontend
cd frontend && npm run build && cd ..

# 2. En Windows, ejecutar como administrador:
# powershell -File scripts/build_windows.ps1
```

## Qué funciona hoy

- CRUD completo de targets, endpoints, findings
- Pipeline de validación con veredictos y evidencia
- Motor de scoring determinista (unified_scoring)
- Motor de clasificación de endpoints
- Daily briefing con oportunidades priorizadas
- Attack surface analysis
- Sistema de oportunidades (48 después de refresh)
- Dashboard de overview con métricas
- Health check de sistema
- Notificaciones internas
- Estado del asistente e inteligencia

## Qué está en desarrollo

- Integración total con frontend React (hoy apunta a puerto 5173)
- Pipeline de recon automático (hoy es bajo demanda)
- Más providers de oportunidades en startup
- Pruebas automatizadas
- Reportes exportables (PDF/CSV)

## API endpoints principales

| Endpoint | Descripción |
|----------|-------------|
| `GET /api/health` | Health check |
| `GET /api/stats` | Estadísticas de la DB (targets, endpoints, findings, etc.) |
| `GET /api/targets` | Listar targets |
| `GET /api/endpoints` | Listar endpoints |
| `GET /api/findings` | Listar findings |
| `GET /api/verdicts` | Listar veredictos |
| `GET /api/evidence` | Listar evidencia |
| `GET /api/daily/briefing` | Briefing diario con oportunidades, risk alerts y quick wins |
| `GET /api/opportunities` | Oportunidades (basadas en pipeline DB) |
| `GET /api/opportunity/top` | Top oportunidades del engine de inteligencia |
| `GET /api/overview` | Vista general |
| `GET /api/attack-surface` | Superficie de ataque |
| `GET /api/pipeline` | Estado del pipeline |
| `POST /api/scans` | Lanzar scan |
| `POST /api/opportunity/refresh` | Refrescar oportunidades |
| `GET /api/system/health` | Salud del sistema |

## Estructura del proyecto

```
Rastro/
├── api/
│   ├── main.py              ← Backend principal (FastAPI)
│   ├── routers/             ← 35 routers endpoint
│   └── services/
│       └── data_service.py  ← Capa de acceso a datos
├── core/
│   ├── engine/              ← Scoring y clasificación
│   ├── recon/               ← Pipeline de descubrimiento
│   ├── validation/          ← Pipeline de validación
│   ├── opportunity/         ← Inteligencia de oportunidades
│   ├── orchestrator/        ← Orquestación
│   ├── memory/              ← Memoria del sistema
│   ├── notifications/       ← Notificaciones
│   └── ...
├── database/
│   ├── db.py                ← Conexión SQLAlchemy
│   ├── models.py            ← Modelos de datos
│   └── rastro.db            ← Base de datos SQLite
├── desktop/
│   ├── main_desktop.py      ← Entrypoint desktop
│   └── serve_frontend.py    ← Servir frontend
├── frontend/
│   └── src/                 ← React + TypeScript (Vite)
├── scripts/
│   ├── bootstrap.py         ← Inicializar DB
│   └── build_windows.ps1    ← Build para Windows
├── main.py                  ← Backend secundario (standalone)
├── Rastro.spec              ← PyInstaller spec
├── PLAN.md                  ← Plan operativo
├── RUNTIME_GAPS.md          ← Gaps de runtime
└── ARCHITECTURE.md          ← Arquitectura
```

## Licencia

Herramienta interna — no para redistribución.
