# Changelog

## v1.6.0 (RC3) — 2026-06-28

### 🚀 Nuevo

- **Build pipeline profesional**: `scripts/build_release.py` — un solo comando construye frontend + backend + instalador + ZIP
- **Instalador NSIS profesional**: Instala en `Program Files`, registra servicio Windows, crea accesos directos, Add/Remove Programs
- **Servicio Windows**: `desktop/service.py` — `Rastro.exe --service` como servicio residente con inicio automático
- **Watchdog interno**: `desktop/watchdog.py` — monitorea API, agentes, scheduler, EventBus, RAM/CPU; auto-recovery con backoff
- **Tray mejorado**: Nuevos menús: View Logs, Open Data Folder, Restart Service, Stop Service, Quit Tray (no detiene backend)
- **Dashboard de salud**: `/api/system/status` — estado completo del sistema, watchdog, agentes, pipeline, memoria, CPU
- **Identity Center**: Gestión de cuentas de plataformas, wallets, email, y flag `never_submit_without_approval`
- **Auto-update**: Sistema completo de actualizaciones vía GitHub Releases con rollback seguro

### 🛡️ Seguridad y Estabilidad

- Cifrado AES-256-GCM para credenciales de plataforma
- Flag "Nunca enviar sin mi aprobación" activado por defecto
- Sesión desktop con auto-autenticación
- SQLite WAL mode + busy_timeout=5000 en todas las conexiones

### ⚡ Rendimiento

- EventSystem con límite FIFO (max 500 eventos) — sin OOM
- SQLite WAL mode + synchronous=NORMAL — sin `database is locked`
- Pipeline state machine con validación de transiciones
- Cache de pipelines con límite

### 🐛 Correcciones

- Pipeline stuck en PAID → CLOSED (`_on_financial_update`)
- Scheduler double-wrapping (`start()`/`stop()` correctos)
- Agent subscriptions sin limpiar en `stop()` (nuevo `unsubscribe_agent()`)
- Retry delay faltante en Coordinator
- OOM en EventSystem
- SQLite "database is locked"
- `useRef` unused en frontend (build roto)
- `_subscription_types` no inicializado en BaseAgent (crash en tests)

---

## v1.5.0 (RC2) — 2026-06-15

- Release Candidate 1
- Arquitectura multi-agente completa
- Pipeline de 11 estados (PENDING → DISCOVERY → VALIDATION → ... → CLOSED)
- Integración con HackerOne, Bugcrowd, Intigriti, YesWeHack, Synack
- Frontend PrimeReact dark mode con 30+ páginas
- 333 tests pasando
- Exportación PDF / HTML / TXT
