<p align="center">
  <img src="https://img.shields.io/badge/version-1.6.0--stable-gold?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/platform-Windows%2011-7c3aed?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/tests-333%20passing-brightgreen?style=flat-square" alt="Tests">
  <img src="https://img.shields.io/badge/license-Proprietary-blue?style=flat-square" alt="License">
</p>

<h1 align="center">ORION</h1>
<p align="center"><em>Autonomous Bug Bounty Intelligence System</em></p>

<p align="center">
  Discover. Score. Validate. Report.<br>
  Your entire bug bounty workflow, automated and running 100% locally.
</p>

---

## Features

| | |
|---|---|
| **Autonomous AI Pipeline** | End-to-end orchestration from target discovery to report submission |
| **Multi-Platform Integration** | HackerOne, Bugcrowd, Intigriti, YesWeHack, Synack |
| **Smart Scoring Engine** | Deterministic heuristic scoring with 15+ signals and confidence gating |
| **Evidence Graph** | Map relationships between findings, endpoints, and attack surfaces |
| **Auto-Healing System** | Self-recovering pipeline with internal watchdog and health monitoring |
| **Professional Reports** | HackerOne/Bugcrowd-ready exports, PDF, Markdown |
| **Identity Vault** | AES-256-GCM encrypted credentials with safe-submit guard |
| **Desktop Native** | System tray, Windows Service, auto-update, offline-capable |

---

## Quick Start

### Windows (Recommended)
1. Download `OrionInstaller.exe`
2. Double-click to install
3. ORION starts automatically in the system tray
4. Open http://127.0.0.1:8000 in your browser

### Portable (No Installation)
1. Download `Orion.zip`
2. Extract to any folder
3. Run `Orion.exe --tray`
4. Open http://127.0.0.1:8000

### Development
```bash
python run.py --install
python run.py --browser
```

---

## Architecture

```
Browser / Desktop App
       |
   FastAPI Backend (47 routers / ~240 endpoints)
       |
   AuthMiddleware -> RateLimitMiddleware -> CORSMiddleware
       |
   Orchestrator -> Agents -> Pipeline (11 states)
       |
   Recon -> Scoring -> Evidence -> Validation -> Report
       |
   SQLite / PostgreSQL (SQLAlchemy)
```

**Frontend:** React 19 + TypeScript + Vite 8 + PrimeReact dark theme

**Desktop:** PyInstaller (single executable), pystray, watchdog, auto-update

---

## Status

| | |
|---|---|
| **Version** | 1.6.0 Stable |
| **Tests** | 333+ passing (pytest) |
| **Pipeline** | 11 stages, fully deterministic |
| **Agents** | 4 specialized agents (Coordinator, Financial, Memory, Exploit) |
| **Runtime** | Local only — no cloud dependency, no data exfiltration |

---

## Project Structure

```
/
├── api/              FastAPI backend (47 routers, ~240 routes)
├── core_engines/     Intelligence core (recon, scoring, validation, evidence, reporting, AI, auth, license)
├── frontend/         React + TypeScript + Vite dashboard
├── desktop/          Desktop app (pywebview, tray, watchdog, updater, Windows Service)
├── database/         SQLAlchemy models + SQLite/PostgreSQL
├── scripts/          Build and utility scripts
├── tests/            Test suite (pytest)
├── installer/        Windows installer (NSIS)
└── run.py            Single entrypoint
```

---

## Links

- [Changelog](CHANGELOG.md)
- [License](LICENSE)
