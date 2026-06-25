<p align="center">
  <img src="https://img.shields.io/badge/version-1.5.0--rc1-7c3aed?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux-7c3aed?style=for-the-badge" alt="Platform">
  <img src="https://img.shields.io/badge/espa%C3%B1ol-default-7c3aed?style=for-the-badge" alt="Spanish Default">
  <img src="https://img.shields.io/badge/license-Proprietary-ef4444?style=for-the-badge" alt="License">
</p>

<h1 align="center">Rastro</h1>
<p align="center"><em>Sistema Operativo Privado de Investigaci&oacute;n</em></p>

<p align="center">
  Rastro es un sistema operativo privado de investigaci&oacute;n para analistas de bug bounty<br>
  y attack surface intelligence. Corre 100% local, sin dependencia cloud.<br>
  <strong>Idioma por defecto: Espa&ntilde;ol</strong> &mdash; con soporte completo para Ingl&eacute;s y arquitectura multi-idioma.
</p>

---

## Descripci&oacute;n

Rastro automatiza el ciclo completo de bug bounty: descubrimiento de activos, scoring heur&iacute;stico, validaci&oacute;n de hallazgos, generaci&oacute;n de reportes y orquestaci&oacute;n de inteligencia. Est&aacute; dise&ntilde;ado para operar de forma completamente local, sin enviar datos a terceros.

### Demo Flow

```
Input Target ---> Recon ---> Scoring ---> Graph ---> Evidence ---> Verdict ---> Report

    1              2           3           4           5            6           7
  name/domain   subfinder   unified_    hot_path    validation   confirmed   HackerOne-
                httpx       scoring     detection   replayer     /rejected   formatted
                katana      classify    clustering  + rules      + conf.     report
                wayback                             + gate       score
```

---

## Arquitectura

```
Middleware: CORSMiddleware -> RateLimitMiddleware -> AuthMiddleware
Backend:    FastAPI + 47 routers / ~240 routes + SQLAlchemy + SQLite/PostgreSQL
Frontend:   React 19 + TypeScript + Vite 8 + 32 pages + 18 components
Desktop:    pywebview + pystray + PyInstaller (single process)
```

### Pipeline Core

```
Recon -> Scoring -> Graph -> Evidence -> Verdict -> Report
  subfinder   unified_    hot_path    replayer    severity
  httpx       scoring     detection   -> rules    -> CVSS
  katana      classify    clustering  -> conf.    -> export
  wayback                             -> gate
```

### Flujo de Ejecuci&oacute;n

1. `run.py` -> bootstrap de rutas, auto-build de frontend si es necesario
2. `desktop/main_desktop.py` -> inicializa API (uvicorn), abre ventana pywebview o navegador
3. FastAPI monta 47 routers con ~240 endpoints
4. AuthMiddleware valida JWT + licencia en cada request autenticado
5. Frontend React se comunica v&iacute;a REST + WebSocket

---

## M&oacute;dulos

| M&oacute;dulo | Descripci&oacute;n |
|--------|-------------|
| `api/` | FastAPI backend con 47 routers, middleware, schemas y servicios |
| `core_engines/` | Motor central (~30 subm&oacute;dulos) |
| `core_engines/recon/` | Pipeline de descubrimiento (subfinder, httpx, katana, etc.) |
| `core_engines/scoring/` | Scoring heur&iacute;stico determin&iacute;stico con 15+ se&ntilde;ales |
| `core_engines/validation/` | Replayer + reglas + confidence scoring + gate |
| `core_engines/evidence/` | Grafo de evidencia y almacenamiento |
| `core_engines/reporting/` | Generaci&oacute;n de reportes (HackerOne, Bugcrowd, Markdown) |
| `core_engines/ai/` | Capa de IA: Ollama, OpenAI, fallback local |
| `core_engines/license/` | Sistema de licencias HMAC-SHA256 + HWID |
| `core_engines/auth/` | Autenticaci&oacute;n JWT + sesiones |
| `core_engines/identity/` | Identity vault y target auth |
| `core_engines/intelligence/` | 22 archivos de inteligencia y an&aacute;lisis |
| `core_engines/learning/` | Sistema de aprendizaje y memoria |
| `core_engines/orchestrator/` | Orquestador de pipelines |
| `core_engines/opportunity/` | Detecci&oacute;n de oportunidades |
| `core_engines/notifications/` | Sistema de notificaciones |
| `core_engines/platform/` | Capa de abstracci&oacute;n del SO |
| `core_engines/gateway/` | Rate limiter, router, versionado |
| `desktop/` | Aplicaci&oacute;n de escritorio (pywebview, tray, updater) |
| `frontend/` | Dashboard React + TypeScript + Vite |
| `database/` | Modelos SQLAlchemy + SQLite |
| `installer/` | Scripts de instalaci&oacute;n para Windows |
| `scripts/` | Scripts de build, utilidades y tests |

---

## Sistema de Licencias

Rastro usa un sistema de licencias con binding a hardware para control de acceso.

### Motor de Licencias

- **Algoritmo**: HMAC-SHA256 con clave embebida en el binario
- **Formato de clave**: `XXXXX-XXXXX-XXXXX-XXXXX-XXXXX` (25 caracteres, 5 grupos de 5)
- **Datos codificados**: version(1) + fecha_emision(6) + fecha_expiracion(6) + prefijo_hw(7) + firma_hmac(5)
- **Ubicaci&oacute;n**: `core_engines/license/`
  - `validator.py` &mdash; validaci&oacute;n de firma, expiraci&oacute;n y binding HW
  - `hardware.py` &mdash; generaci&oacute;n de HWID multi-factor
  - `store.py` &mdash; persistencia de licencia + binding en disco

### Sistema HWID

El HWID (Hardware ID) se genera combinando:

1. **Hostname** &mdash; `socket.gethostname()`
2. **MAC address** &mdash; Primera interfaz no virtual (`uuid.getnode()`)
3. **Machine ID** &mdash; Fuentes m&uacute;ltiples con dedup:
   - Linux: `/etc/machine-id`, `/var/lib/dbus/machine-id`
   - Windows: Registry `HKLM\\SOFTWARE\\Microsoft\\Cryptography\\MachineGuid`
   - Fallback: `$HOSTNAME` / `$COMPUTERNAME`

Se calcula: `SHA256(hostname|mac|machine_id)[:32]`

### Flujo de Activaci&oacute;n

1. **Primera activaci&oacute;n**: La clave se valida (firma HMAC + expiraci&oacute;n) y se bindea al HWID actual
2. **Ejecuciones posteriores**: Se verifica que el HWID actual coincida con el almacenado
3. **Auto-heal**: Si cambia el HWID completo pero el prefijo de 7 caracteres coincide, se re-bindea autom&aacute;ticamente (tolerante a cambios menores de hardware)
4. **Rechazo**: Si el prefijo HWID no coincide, se rechaza con "Hardware mismatch"

### API de Licencias

| Endpoint | M&eacute;todo | Descripci&oacute;n |
|----------|--------|-------------|
| `/api/license/status` | GET | Estado de la licencia actual |
| `/api/license/activate` | POST | Activar una clave de licencia |
| `/api/license/deactivate` | POST | Desactivar (limpiar) la licencia |

---

## Compilaci&oacute;n

### Requisitos

- Python 3.10+ (3.12+ recomendado)
- Node.js 20+
- NPM 9+

### Dependencias

```
# Python (requirements.txt)
fastapi, uvicorn, sqlalchemy, pydantic, httpx, requests, rich, ollama,
plotly, pandas, jinja2, cvss, psutil, pywebview, pystray, plyer, Pillow,
python-dotenv, psycopg2-binary, cryptography

# Frontend (frontend/package.json)
React 19, TypeScript 6, Vite 8, Tailwind 4, TanStack Query, Zustand 5,
Framer Motion, react-router-dom 7, Radix UI, cmdk
```

### Build de Windows (WSL)

```bash
python scripts/build_windows_exe.py
```

Este script:
1. Copia los archivos del proyecto a un directorio temporal en Windows
2. Ejecuta PyInstaller via Python de Windows (WSL interop)
3. Limpia el directorio temporal al finalizar

### Build de Linux

```bash
scripts/build_linux.sh
```

### Build Manual (cualquier plataforma)

```bash
# 1. Entorno virtual
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Frontend
cd frontend && npm ci && npm run build && cd ..

# 3. PyInstaller
pyinstaller Rastro.spec -y

# El binario queda en dist/Rastro/
```

### Makefile

```bash
make build-desktop      # Build PyInstaller (SO actual)
make install-windows    # Build + portable ZIP + NSIS
make build-android      # Build APK (requiere Android SDK)
make clean              # Limpiar artifacts de build
```

---

## Estructura del Proyecto

```
.
+-- api/                    # FastAPI backend
|   +-- main.py             # Entrypoint + startup sequence
|   +-- middleware/          # CORS -> RateLimit -> Auth
|   +-- routers/            # 47 routers, ~240 routes
|   +-- schemas/            # Modelos Pydantic
|   +-- services/           # Data access layer
+-- core_engines/            # Core intelligence (~30 modulos)
|   +-- ai/                 # Conversational AI (Ollama/OpenAI)
|   +-- auth/               # JWT + sesiones
|   +-- engine/             # Scoring + clasificacion
|   +-- evidence/           # Grafo de evidencia
|   +-- intelligence/       # Inteligencia y analisis
|   +-- learning/           # Sistema de aprendizaje
|   +-- license/            # HMAC-SHA256 licensing + HWID
|   +-- notifications/      # Sistema de notificaciones
|   +-- opportunity/        # Deteccion de oportunidades
|   +-- orchestrator/       # Orquestacion de pipelines
|   +-- platform/           # Abstraccion del SO
|   +-- recon/              # Pipeline de descubrimiento
|   +-- reporting/          # Generacion de reportes
|   +-- validation/         # Validacion de hallazgos
|   +-- ...                 # ~30 modulos total
+-- frontend/               # React + TypeScript + Vite
|   +-- src/
|   |   +-- components/     # 18 componentes
|   |   +-- pages/          # 32 paginas con lazy loading
|   |   +-- stores/         # 7 slices Zustand
|   |   +-- lib/            # API, i18n, utilidades
|   |   +-- types/          # TypeScript definitions
|   +-- public/             # Assets estaticos
+-- desktop/                # Aplicacion de escritorio
|   +-- main_desktop.py     # 13-step boot sequence
|   +-- serve_frontend.py   # Servidor de archivos estaticos
|   +-- tray.py             # Bandeja del sistema
|   +-- updater.py          # Auto-actualizacion
|   +-- build/              # Scripts de build
+-- database/               # SQLAlchemy + SQLite
|   +-- models.py           # 15 modelos
|   +-- rastro.db           # Base de datos SQLite
+-- installer/              # Instalador Windows
|   +-- install_windows.ps1
|   +-- uninstall_windows.ps1
+-- scripts/                # Scripts de build y utilidades
|   +-- build_windows_exe.py  # Build Windows EXE (entry point unico)
|   +-- build_windows.ps1     # Build Windows (PowerShell nativo)
|   +-- build_linux.sh        # Build Linux
|   +-- install_windows.py    # Instalador Windows
|   +-- prebuild.py           # Validacion pre-build
|   +-- build_android.py      # Build Android APK
|   +-- release.py            # Git release automation
|   +-- ...                   # Utilidades adicionales
+-- tests/                  # Suite de tests
|   +-- conftest.py
|   +-- test_api_endpoints.py
|   +-- test_auth_users.py
|   +-- test_contracts.py
|   +-- test_desktop_release.py
|   +-- test_e2e_flow.py
|   +-- test_intelligence_loop.py
|   +-- test_learning.py
|   +-- test_pipeline_e2e.py
|   +-- test_scheduler.py
|   +-- test_scoring.py
|   +-- test_security.py
|   +-- test_tools.py
+-- android/                # Proyecto Android (Capacitor)
|   +-- app/                # Aplicacion Android nativa
+-- run.py                  # Entrypoint principal
+-- Rastro.spec             # PyInstaller spec
+-- requirements.txt        # Dependencias Python
+-- VERSION                 # Version actual (1.5.0)
+-- Makefile                # Comandos de build
```

---

## Inicio Rapido

```bash
# Produccion (desde ZIP -- extraer y ejecutar)
cd Rastro-Desktop && ./run.sh

# Desarrollo
cd frontend && npm run dev              # Terminal 1
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000   # Terminal 2
```

| Servicio | URL |
|----------|-----|
| API | http://127.0.0.1:8000 |
| Frontend (dev) | http://localhost:5173 |
| Documentacion API | http://127.0.0.1:8000/api/docs |

---

## Troubleshooting

### La ventana no se abre

Verificar que el frontend este compilado:
```bash
cd frontend && npm ci && npm run build
```

### Error de licencia

1. Verificar que el archivo `license.json` existe en `%APPDATA%/Rastro/` (Windows) o `~/.local/share/Rastro/` (Linux)
2. Si el HWID cambio (ej: despues de actualizar hardware), reactivar con la misma clave
3. Si persiste, eliminar `license.json` y reactivar

### El build de Windows falla

1. Verificar que Python 3.12+ este instalado en Windows
2. Verificar que PyInstaller este instalado: `pip install pyinstaller`
3. Ejecutar con `--keep-temp` y revisar los logs en el directorio temporal

### Los tests no pasan

```bash
source .venv/bin/activate
python -m pytest tests/ -v --tb=long
```

---

## Changelog 1.5.0 RC1

### Cambios principales
- Release engineering: limpieza completa del repositorio
- Eliminacion de ~8,500 lineas de documentacion duplicada y codigo muerto
- Eliminacion de 2.1 GB de builds antiguos y artifacts
- Eliminacion de todo el codigo de diagnostico temporal (MessageBox, logs HWID, startup_diag)
- Preservacion del auto-heal en el sistema de licencias

### Sistema de licencias
- Eliminados MessageBox de depuracion en validacion HWID
- Eliminados logs de diagnostico a `license_diagnostic.log`
- Preservado el comportamiento auto-heal (re-bindeo automatico en cambios menores de HW)
- Codigo limpio sin instrumentacion de desarrollo

### Build
- Unificado el sistema de compilacion en un solo entry point: `scripts/build_windows_exe.py`
- Eliminados 13 scripts de build obsoletos o duplicados
- Sin rutas hardcodeadas (configurables via argumentos CLI)
- Auto-limpieza del directorio temporal al finalizar

### Documentacion
- README unico y completo con toda la informacion del proyecto
- Eliminados 43+ archivos de documentacion duplicada

### General
- Reduccion de tamano del proyecto: ~2.2 GB liberados
- Codigo fuente limpio, sin prints de debugging ni instrumentacion
- Tests preservados y verificados
- Checklist de release completamente documentada

---

## Licencia

Proprietary -- internal use. Redistribution prohibited without authorization.

---

<p align="center"><em>Built with  for serious researchers</em></p>
