# Changelog

## v1.6.0 (Stable) — 2026-06-29

### 🚀 Release
- ORION v1.6.0 Stable — primer release instalable profesional
- Build pipeline reproducible con un solo comando
- NSIS installer con instalación en Program Files, accesos directos, Add/Remove Programs
- PyInstaller single-directory executable
- Wonder fully isolated from development environment

### 🛡️ Estabilidad
- Watchdog interno con auto-recovery
- Sistema de auto-healing con backoff exponencial
- Rollback seguro en actualizaciones fallidas
- Arquitectura monoproceso — sin subprocess, sin multiprocessing

### ⚡ Rendimiento
- EventSystem con límite FIFO (max 500 eventos)
- SQLite WAL mode + synchronous=NORMAL
- Cache de pipelines con límite

---

## v1.6.0 (RC3) — 2026-06-28

### 🚀 Nuevo
- Build pipeline profesional
- Instalador NSIS profesional
- Servicio Windows
- Watchdog interno
- Identity Center
- Auto-update con rollback seguro

### 🛡️ Seguridad y Estabilidad
- Cifrado AES-256-GCM para credenciales
- Flag "Nunca enviar sin aprobación"
- Sesión desktop con auto-autenticación

### 🐛 Correcciones
- Pipeline stuck en PAID → CLOSED
- Scheduler double-wrapping
- Agent subscriptions sin limpiar
- Retry delay faltante en Coordinator
- OOM en EventSystem
- SQLite "database is locked"

---

## v1.5.0 (RC2) — 2026-06-15

- Release Candidate 1
- Arquitectura multi-agente completa
- Pipeline de 11 estados
- Integración con HackerOne, Bugcrowd, Intigriti, YesWeHack, Synack
- Frontend PrimeReact dark mode con 30+ páginas
- 333+ tests pasando
- Exportación PDF / HTML / TXT
