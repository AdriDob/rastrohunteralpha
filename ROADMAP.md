# ROADMAP — RASTRO INVESTIGATION OS
**Versión:** Alpha 0.4
**Fecha:** Junio 2026
**Visión:** Convertir Rastro en un **Sistema Operativo Privado de Investigación** para analistas de bug bounty y attack surface intelligence.

## 1. Estado Actual Real del Sistema

Rastro ha alcanzado un estado **Alpha funcional estable — UX transformation completada**:

- **Backend estable**: FastAPI + SQLAlchemy + SQLite con 183 rutas operativas, 0 deprecation warnings.
- **Base de datos**: SQLite única (`database/rastro.db`) con seed data: 5 targets, 50 endpoints, 8 findings, 54 verdicts, 834 memory_records.
- **Discovery Engine**: Subfinder, Katana, Httpx operativos vía Go binaries con scheduler async.
- **Frontend**: React 19 + Vite 8, build en ~0.9s, 0 errores TypeScript, 22 páginas con lazy loading.
- **AI Layer**: Ollama (Qwen2.5-Coder) + OpenAI-compatible + fallback local rule-based.
- **Investigation Narrator**: 7 funciones de interpretación de inteligencia.
- **Test suite**: 107/107 passed.
- **Gaps resueltos**: 9 gaps identificados, 7/9 corregidos (incluyendo build fix, deprecation warnings, housekeeping).
- **UX OS completo**: Command Palette con shortcuts, AI Copilot contextual, Sidebar extraída, Dashboard con Quick Actions.

El núcleo técnico es sólido. La experiencia de uso está elevada a nivel de sistema operativo de investigación.

## 2. Arquitectura Real Observada

- **Backend**: FastAPI modular con 36 routers independientes (`api/routers/`)
- **Base de datos**: SQLite (`database/rastro.db`) con modelos SQLAlchemy — única autoritativa
- **Frontend**: React + Vite + TypeScript (carpeta `/frontend/`)
- **Recon**: Herramientas CLI (subfinder, katana, httpx) invocadas desde Python
- **AI**: Ollama local + OpenAI-compatible + reglas locales
- **Assistant Layer**: `core/ai/` (conversacional) + `core/assistant/` (narrativo/interpretativo)
- **Launcher**: `launcher/start.py` para orquestar backend + dashboard

## 3. UX Transformation Phase (Investigation OS) — COMPLETADO

**Objetivo principal de esta fase:**
Transformar Rastro de una "herramienta" a un **entorno de investigación privado**, rápido y de baja fricción.

**Pilares clave (completados):**
- **Mission-First Dashboard**: Quick Actions bar + auto-select target + misión del día destacada.
- **AI Copilot Contextual**: Sugerencias cambian según ruta actual (/target/, /evidence/, /insights/).
- **Command Palette** (`Ctrl + K`): Shortcuts visibles (`g m`, `g d`), recent targets, badges por sección.
- **Investigation Narrator**: Interpretación automática del estado del sistema (7 endpoints).
- **Minimal Cognitive Load**: Layout simplificado (-81% en Layout.tsx), sidebar en componente propio.
- **Desktop-first mindset**: Preparado para futura aplicación nativa Windows.

## 4. Features Existentes (Verificadas)

- Motor de descubrimiento (subfinder, katana, httpx)
- Persistencia de endpoints y findings
- Sistema de scoring de oportunidades (v1 + v2 layered)
- Dashboard con 22 páginas y navegación completa
- Gestión de targets con favoritos y recientes
- API endpoints estables (183 rutas, 100% funcionales)
- Launcher unificado
- Seed de datos demo
- **Investigation Narrator**: 7 funciones de interpretación de inteligencia
- **AI Copilot**: Briefing diario, bounty potential, sugerencias contextuales por ruta
- **Command Palette**: Shortcuts keyboard + recent targets + badges + búsqueda dinámica
- **Sidebar**: Componente extraído, colapsable, persistente, búsqueda, favoritos, 6 secciones
- **Dashboard**: Mission Widget + Quick Actions bar + auto-select target
- **Housekeeping**: 0 DB duplicadas, 0 deprecation warnings, build en 0.9s

## 5. Issues Conocidos (Baja Prioridad)

- GAP-008: `targets_intel` tiene 5 filas con campos NULL — datos incompletos
- GAP-009: 3 scan_runs stuck en "running" — registros huérfanos
- Widget drag & drop (pendiente definición arquitectónica)

## 6. Ideas Avanzadas (Experimental / "Locas" pero útiles)

- **"Today's Mission"**: ✅ Implementado — MissionWidget + Quick Actions
- **AI Memory de Sesión**: El asistente recuerda qué estabas investigando ayer y te ofrece "¿Continuamos con el target X?".
- **Zero-Click Insights**: ✅ Parcial — Briefing se carga al abrir Rastro
- **Replay Timeline Visual**: Ver la evolución de un target como una película (cambios en endpoints, findings nuevos, etc.).
- **Predictive Navigation**: Sugerir "¿Quieres ver los endpoints con IDOR?" basado en tu historial.
- **Investigation Canvas**: Espacio infinito donde arrastrar evidencias, conectar hallazgos y construir hipótesis visualmente.
- **One-Click Report**: ✅ Parcial — ReportNarrative implementado en InvestigationNarrator
- **Attack Path Visualization**: ✅ Parcial — explain_attack_path en InvestigationNarrator
- **Unified Web2+Web3 Dashboard**: ✅ Parcial — unified_intelligence en InvestigationNarrator
- **Auto-generated Intelligence Briefing**: PDF ejecutivo generado automáticamente cada 24h.

## 7. Roadmap Futuro (Incremental)

**Q3 2026 (Beta)**
- ✅ UX Transformation completa (100%)
- ✅ Command Palette + AI Copilot contextual (completado)
- ✅ Sidebar extraída (completado)
- ✅ Dashboard con Quick Actions (completado)
- ✅ Housekeeping (DB única, 0 deprecation warnings)
- ⬜ Widget system con drag & drop
- ⬜ Desktop packaging (Windows .exe) estable
- ⬜ Modo offline básico

**Q4 2026**
- Investigation Canvas
- Advanced Replay & Differential Engine visual
- Multi-target workspace
- Exportable investigation packages

**2027 (Versión 1.0)**
- Versión nativa Windows + Linux
- AI Memory persistente entre sesiones
- Soporte para equipos (opcional)
- Integraciones con herramientas externas (Burp, Nuclei, etc.)

## 8. Riesgos de Evolución

- Sobrecarga cognitiva si se agregan demasiados widgets
- Dependencia excesiva de AI → usuario pierde agency
- Complejidad del packaging Windows (PyInstaller + assets)
- Mantenimiento de compatibilidad entre backend y frontend
- Rendimiento con grandes volúmenes de endpoints
- La capa InvestigationNarrator hace queries complejas a DB — monitorear con datasets grandes

---

**Próximo paso recomendado:**
Widget system con drag & drop, o comenzar packaging desktop para Windows.
