<p align="center">
  <img src="https://img.shields.io/badge/version-1.4.0--rc1-7c3aed?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/tests-159%20passing-22c55e?style=for-the-badge" alt="Tests">
  <img src="https://img.shields.io/badge/build-0%20errors-22c55e?style=for-the-badge" alt="Build">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-7c3aed?style=for-the-badge" alt="Platform">
  <img src="https://img.shields.io/badge/español-default-7c3aed?style=for-the-badge" alt="Spanish Default">
  <img src="https://img.shields.io/badge/license-Proprietary-ef4444?style=for-the-badge" alt="License">
</p>

<h1 align="center">🕵️ Rastro</h1>
<p align="center"><em>Sistema Operativo Privado de Investigación</em></p>

<p align="center">
  Rastro es un sistema operativo privado de investigación para analistas de bug bounty<br>
  y attack surface intelligence. Corre 100% local, sin dependencia cloud.<br>
  <strong>Idioma por defecto: Español</strong> — con soporte completo para Inglés y arquitectura multi-idioma.
</p>

---

## Demo Flow

```
Input Target ──→ Recon ──→ Scoring ──→ Graph ──→ Evidence ──→ Verdict ──→ Report

    1              2           3           4           5            6           7
  name/domain   subfinder   unified_    hot_path    validation   confirmed   HackerOne-
                httpx       scoring     detection   replayer     /rejected   formatted
                katana      classify    clustering  + rules      + conf.     report
                wayback                             + gate       score
```

1. **Input**: Bug bounty target (domain or URL)
2. **Recon**: Subfinder → httpx → katana → waybackurls → endpoint parser
3. **Scoring**: Deterministic heuristic scoring per endpoint (no ML)
4. **Graph**: Hot path detection + attack surface clustering
5. **Evidence**: Replay + rule engine + confidence scoring + gate admission
6. **Verdict**: Confirmed / Rejected / Inconclusive with confidence score
7. **Report**: HackerOne JSON, Bugcrowd HTML, or Markdown export

---

## Quick Start

```bash
# Production (desktop mode)
python desktop/main_desktop.py

# Development
cd frontend && npm run dev   # Terminal 1
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000   # Terminal 2
```

| Service | URL |
|---------|-----|
| API | http://127.0.0.1:8000 |
| Frontend (dev) | http://localhost:5173 |
| API docs | http://127.0.0.1:8000/api/docs |

---

## Features

| Layer | Capabilities |
|-------|-------------|
| **Auth & Security** | JWT middleware, rate limiter (token bucket), license system (HMAC-SHA256), hardware fingerprint |
| **Discovery** | Subfinder, httpx, katana, waybackurls — async pipeline with 30min scheduler |
| **Scoring** | Deterministic `unified_scoring()` with LRU cache, 15+ heuristic signals |
| **Graph** | Hot path detection, attack surface clustering, differential intelligence |
| **Validation** | Replayer → rules engine → confidence scoring → gate admission |
| **Reporting** | HackerOne JSON, Bugcrowd HTML, Markdown, CVSS v3 severity |
| **AI Layer** | Ollama (Qwen2.5-Coder) + OpenAI-compatible + local rule-based fallback |
| **Investigation Narrator** | 7 auto-interpretation functions: state, narrative, attack path, bounty potential, daily briefing |
| **UX** | React 19 + Vite 8 + Tailwind 4 + framer-motion; Command Palette (Ctrl+K), AI Copilot, onboarding tour |
| **Desktop** | pywebview 6 + pystray tray + PyInstaller; auto-updater with SHA-256 rollback |
| **Packaging** | Windows (PyInstaller + NSIS), Linux (PyInstaller + AppImage), auto-updater via GitHub Releases |

---

## Architecture

```
Middleware: CORSMiddleware → RateLimitMiddleware → AuthMiddleware
Backend:    FastAPI + 44 routers / ~236 routes + SQLAlchemy + SQLite/PostgreSQL
Frontend:   React 19 + TypeScript + Vite 8 + 28 pages
Desktop:    pywebview + pystray + PyInstaller (single process)
```

Key modules: `core_engines/` — recon, scoring, graph, evidence, verdict, report, AI, auth, license, platform.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full breakdown.

---

## Project Structure

<details>
<summary>Click to expand</summary>

```
.
├── api/                    # FastAPI backend
│   ├── main.py             # App entrypoint + 25-step startup
│   ├── middleware/          # CORS → RateLimit → Auth
│   ├── routers/            # 44 routers, ~236 routes
│   └── services/           # Data access layer
├── core_engines/            # Core intelligence
│   ├── engine/             # Scoring + classification
│   ├── recon/              # Discovery pipeline
│   ├── validation/         # Replay → rules → gate
│   ├── evidence/           # Evidence graph + store
│   ├── analysis/           # Graph builder + clustering
│   ├── reporting/          # Report generation + export
│   ├── ai/                 # Conversational AI (Ollama/OpenAI)
│   ├── assistant/          # Investigation Narrator
│   ├── license/            # HMAC-SHA256 licensing
│   ├── auth/               # JWT auth manager
│   ├── gateway/            # Rate limiter, router, version
│   ├── platform/           # OS abstraction layer
│   └── ...                 # 30+ modules total
├── frontend/               # React + TypeScript + Vite
│   └── src/                # 27 pages, 24 components
├── desktop/                # Desktop app entrypoint
│   ├── main_desktop.py     # 13-step boot sequence
│   ├── updater.py          # Auto-updater + rollback
│   └── serve_frontend.py   # Static file serving
├── installer/              # Windows installer scripts
│   ├── install_windows.ps1
│   ├── uninstall_windows.ps1
│   └── install_windows.nsi # NSIS installer
├── scripts/
│   ├── build_linux.sh      # PyInstaller build
│   ├── build_windows.ps1   # Windows build
│   └── build_appimage.sh   # AppImage build
├── database/
│   ├── models.py           # 15 SQLAlchemy models
│   └── rastro.db           # SQLite database
├── tests/                  # 122 tests (security + API + tools)
├── docs/
│   └── android_build.md    # Android Capacitor guide
└── Rastro.spec             # PyInstaller configuration
```
</details>

---

## Downloads

| Platform | Format | How to Get |
|----------|--------|------------|
| Windows 10/11 | `.exe` + NSIS installer | GitHub Releases (CI build) |
| Linux (x86_64) | PyInstaller bundle | `scripts/build_linux.sh` |
| Linux (x86_64) | `.AppImage` | `scripts/build_appimage.sh` |
| Android | APK | See `docs/android_build.md` |

```bash
# Linux — run directly
./dist/Rastro/Rastro

# Linux — AppImage (portable single file)
./dist/Rastro-1.0.0-x86_64.AppImage

# Windows — double-click installer
Rastro_Setup_1.0.0.exe
```

---

## System Requirements

- **OS**: Windows 10/11, Linux (x86_64), macOS (experimental)
- **Python**: 3.10+ (3.14 recommended)
- **RAM**: 512 MB minimum, 2 GB recommended
- **Disk**: 500 MB for installation
- **Optional tools**: subfinder, httpx, katana (Go binaries)

---

## License

Proprietary — internal use. Redistribution prohibited without authorization.

---

<p align="center"><em>Built with 🕵️ for serious researchers</em></p>
