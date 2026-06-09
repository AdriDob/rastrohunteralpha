# Rastro — Attack Surface Intelligence

Semi-autonomous bug bounty recon and attack surface analysis system.
Centralized intelligence engine with deterministic scoring, noise reduction,
and snapshot-based reporting.

## Quick Start

```bash
git clone <repo>
cd Rastro
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Full stack (backend + dashboard)
python launcher/start.py

# Demo mode (fake dataset, no external tools needed)
python launcher/start.py --demo
```

### URLs

| Service    | URL                         |
|------------|-----------------------------|
| API        | http://127.0.0.1:8000       |
| Dashboard  | http://localhost:8501        |

## Architecture

```
                    ┌─────────────────────┐
                    │  Recon Pipeline      │
                    │  (subfinder/katana/  │
                    │   httpx/wayback)     │
                    └────────┬────────────┘
                             │ raw endpoints
                             ▼
                    ┌─────────────────────┐
                    │  core/engine/        │ ← SINGLE SOURCE OF TRUTH
                    │  unified_scoring.py  │
                    │  unified_classifier  │
                    │  risk_model.py       │
                    └────────┬────────────┘
                             │ scored + classified endpoints
                             ▼
                    ┌─────────────────────┐
                    │  Pipeline            │
                    │  (noise reduction →  │
                    │   investigation →    │
                    │   validation →       │
                    │   reporting)         │
                    └────────┬────────────┘
                             │ PipelineSnapshot
                             ▼
                    ┌─────────────────────┐
                    │  Dashboard (read)    │
                    │  API (read + write)  │
                    └─────────────────────┘
```

## Requirements

| Dependency   | Required | Notes                            |
|-------------|----------|----------------------------------|
| Python 3.10+ | Yes     |                                  |
| Ollama       | Optional | AI summaries (qwen2.5-coder)     |
| subfinder    | Optional | Subdomain discovery              |
| katana       | Optional | Web crawling                     |
| httpx        | Optional | HTTP probing                     |

## Structure

```
Rastro/
├── core/engine/          ← Intelligence engine (SSOT)
│   ├── unified_scoring.py   score(), score_target()
│   ├── unified_classifier   classify(), synthesize_target_meta()
│   ├── risk_model.py        Noise reduction, IDOR, ROI
│   ├── snapshot.py          PipelineSnapshot (immutable reports)
│   └── guardrails.py        Architectural enforcement
├── core/orchestrator/    Pipeline orchestration
├── core/attack/          Attack decision engine
├── core/analysis/        Investigation graph, noise reduction
├── core/validation/      Validation loop, evidence, verdicts
├── core/reporting/       Report generation, CVSS, exports
├── core/recon/           External tool integration
├── core/targets/         Target intelligence (hunter)
├── dashboard/            Streamlit dashboard (read-only)
├── launcher/start.py     One-command launcher
├── main.py               FastAPI backend
└── legacy/               Deprecated scoring modules
```

## API

| Endpoint                    | Description                     |
|-----------------------------|---------------------------------|
| `GET /`                     | Health check                    |
| `POST /targets`             | Create target                   |
| `GET /targets`              | List targets                    |
| `POST /endpoints`           | Create endpoint                 |
| `GET /endpoints`            | List endpoints                  |
| `GET /digest`               | High-signal endpoints           |
| `GET /attack/decision`      | Attack vectors + suggestions    |
| `POST /findings/validate`   | Full validation pipeline        |
| `GET /verdicts`             | List verdicts                   |
| `GET /findings`             | List findings                   |

## License

Internal tool — not for redistribution.
