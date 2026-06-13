# Rastro — Investigation OS

> **Estado:** Alpha 0.4 · **Build:** 0 errores · **Tests:** 107/107 · **APIs:** 183

---

## ¿Qué es Rastro?

Rastro es un **Sistema Operativo de Investigación Privado** para analistas de bug bounty y attack surface intelligence.

No es un escáner. No es un dashboard. Es un entorno de trabajo donde:

- Cargas un target → Rastro descubre automáticamente su superficie de ataque
- Evalúa hallazgos con scoring contextual multicapa
- Te presenta cada mañana una **Misión del Día** priorizada
- Un AI Copilot interpreta los datos y sugiere el próximo movimiento

---

## ¿Qué problema resuelve?

Los bug bounty hunters manejan múltiples targets, cientos de endpoints, findings que aparecen y desaparecen, y oportunidades que caducan. El problema no es falta de datos, es **gestionar la sobrecarga**.

Rastro resuelve:

| Problema | Solución |
|----------|----------|
| ¿Qué investigar hoy? | Misión del Día con scoring y EVH |
| Cientos de endpoints | Pipeline de descubrimiento automático |
| Findings que se pierden | Scoring contextual + priorización |
| Contexto del target | Investigation Narrator con análisis automático |
| Fricción del teclado | Command Palette (Ctrl+K) con 30+ comandos |
| Sesión distribuida | AI Copilot con briefings diarios |

---

## Flujo de usuario

```
1. Abrir Rastro → Mission Control con la misión del día
2. Quick Actions: Run Scan / Hot Paths / Briefing / Oportunidades
3. Discovery automático (subfinder → katana → httpx)
4. Findings evaluados con scoring multicapa (técnico + negocio + prioridad)
5. AI Copilot sugiere el próximo movimiento
6. Dashboard con KPIs, EVH rankings, health de fuentes
7. Exportar / Reportar cuando el target está maduro
```

---

## Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                  Desktop (pywebview)                  │
│  ┌───────────────────────────────────────────────┐  │
│  │           React SPA (Vite 8)                  │  │
│  │  MissionControl · CommandPalette · Sidebar    │  │
│  │  AICopilot · Dashboard · 22 páginas           │  │
│  └──────────────────┬────────────────────────────┘  │
│                     │ HTTP (127.0.0.1:8000)          │
│  ┌──────────────────▼────────────────────────────┐  │
│  │          FastAPI Backend (36 routers)          │  │
│  │  Targets · Endpoints · Findings · Pipeline    │  │
│  │  Scans · Evidence · Intelligence · Reports    │  │
│  │  AI · Auth · Sync · Notifications · Identity  │  │
│  │  Execution · Orchestrator · System             │  │
│  └──────────────────┬────────────────────────────┘  │
│                     │                                │
│  ┌──────────────────▼────────────────────────────┐  │
│  │     SQLite (database/rastro.db) + SQLAlchemy    │  │
│  │     Discovery: subfinder/katana/httpx (Go)      │  │
│  │     AI: Ollama (Qwen) / OpenAI / Rule-based     │  │
│  └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Stack técnico

| Capa | Tecnología |
|------|-----------|
| Frontend | React 19, TypeScript, Vite 8, Zustand, TanStack Query/Table, Tailwind CSS |
| Backend | Python 3.14, FastAPI, SQLAlchemy, Pydantic v2 |
| DB | SQLite (`database/rastro.db`) |
| Discovery | subfinder, katana, httpx (Go binaries) |
| AI | Ollama, OpenAI-compatible, fallback rule-based |
| Desktop | pywebview (Windows/Linux/macOS), pystray, PyInstaller |

---

## Instalación

### Windows (ejecutable)

1. Descargar `Rastro.exe` del release
2. Ejecutar → se abre como app de escritorio
3. (Opcional) Ejecutar `install_windows.ps1` como admin para registro en menú inicio

### Desde código (dev)

**Requisitos:** Python 3.10+, Node.js 20+, Go 1.22+

```bash
git clone https://github.com/tu-usuario/rastro.git
cd rastro

# Backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install && npm run build && cd ..

# Ejecutar (dev)
python desktop/main_desktop.py --dev
```

### Ejecutar en modo navegador

```bash
python desktop/main_desktop.py --dev --browser
```

### Ejecutar con launcher clásico

```bash
python launcher/start.py
```

---

## Features principales

### Misión del Día
Widget principal en Mission Control que prioriza automáticamente el target con mayor potencial, mostrando score, EVH, esfuerzo estimado, confianza y CTA directa.

### AI Copilot Contextual
Panel lateral que ofrece sugerencias según la página actual. En un target muestra Surface + Insights + Bounty. En evidence muestra Pipeline + Hypothesis + Confidence.

### Command Palette (Ctrl+K)
Acceso instantáneo a 30+ comandos con shortcuts visuales (`g m` → Mission Control, `g d` → Daily Mode), secciones con badges y targets recientes.

### Investigation Narrator
7 endpoints de interpretación automática: narrativa de investigación, explicación de rutas de ataque, potencial de bounty, briefing diario, reporte de inteligencia unificado Web2+Web3.

### Dashboard Modular
4 dashboards (Mission Control, Operations, Intelligence, Confidence) con KPIs, gráficas, rankings EVH, health de fuentes de descubrimiento.

### Discovery Pipeline Automático
subfinder (subdominios) → katana (crawling) → httpx (probes HTTP) con scheduler async y cola de tareas.

### Scoring Multicapa
Evaluación combinada de: severidad técnica, impacto de negocio, prioridad contextual, EVH (Expected Value Per Hour), confianza estadística.

---

## Estado actual

| Dimensión | Estado |
|-----------|--------|
| APIs backend | 183 rutas, 36 routers, 100% funcionales |
| Tests | 107/107 passed, 0 deprecation warnings |
| Frontend | Build ~900ms, 0 errores TypeScript, 22 páginas |
| DB | SQLite con seed data (5 targets, 50 endpoints, 8 findings, 54 verdicts) |
| Desktop | pywebview native window + system tray + PyInstaller packaging |
| Gaps conocidos | 0 críticos, 2 cosméticos (datos incompletos en targets_intel) |

### Roadmap resumido

| Hito | Timeline | Estado |
|------|----------|--------|
| UX Transformation (5 fases) | Q2 2026 | ✅ Completo |
| Widget system drag & drop | Q3 2026 | ⬜ Pendiente |
| Desktop packaging (.exe) | Q3 2026 | 🔄 En progreso |
| Modo offline | Q3 2026 | ⬜ Pendiente |
| Investigation Canvas | Q4 2026 | ⬜ Pendiente |
| Versión 1.0 | 2027 | ⬜ |

---

## Links

- `PLAN.md` — Estado detallado del sistema
- `ROADMAP.md` — Roadmap completo
- `desktop/` — Código de empaquetado desktop
- `frontend/` — Código frontend React
- `api/` — Código backend FastAPI
- `database/` — Esquema y migraciones
- `core/` — Lógica de negocio (scoring, AI, pipeline, evidence)
