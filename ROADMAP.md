# Rastro Roadmap

## Phase 1: Core Operational Loop (Current)

### Objectives
Implement a stable, end-to-end bug bounty reconnaissance and analysis system with clear data flow, deterministic scoring, and a practical dashboard.

### Completed ✅

#### Recon Pipeline
- [x] Subfinder integration (subdomain discovery)
- [x] Wayback integration (historical URL collection)
- [x] Katana integration (web crawling and fingerprinting)
- [x] HTTPx integration (API/service endpoint scanning)
- [x] Timeout and subprocess isolation
- [x] Structured JSON outputs
- [x] Async pipeline orchestration

#### Endpoint Processing
- [x] Endpoint normalization (UUID, hex ID, numeric ID detection)
- [x] Path extraction and cleaning
- [x] Deduplication by normalized path + labels + auth smells
- [x] Parameter extraction and storage
- [x] Auth smell detection (org_id, tenant_id, workspace_id, etc.)
- [x] Label classification (/api, /graphql, /admin, /export, /internal)
- [x] Admin and export endpoint flagging

#### Scoring Engine
- [x] Heuristic-based endpoint risk scoring (0-100)
- [x] Target quality scoring (SaaS, B2B, multi-tenant, admin, GraphQL)
- [x] Deterministic weights (no ML)
- [x] Clear signal keywords and auth smell patterns

#### Digest Engine
- [x] High-signal endpoint summary generation
- [x] Top 20 endpoints by risk score
- [x] Risk score sorting
- [x] Target and endpoint metadata inclusion

-#### Dashboard (Streamlit)
- [x] 9-tab layout: Targets, Recon, Endpoints, High Signal, Attack Decision, Findings, Daily Digest, Logs, Targets Intelligence
- [x] Target creation and listing
- [x] Target metadata display
- [x] Recon tab with mode selector (FAST, DEEP, API)
- [x] Scan execution UI
- [x] Endpoint browsing and risk scoring
- [x] Findings view (severity-based)
- [x] Daily digest display
- [x] Scan logs viewer
- [x] Backend connectivity status indicator

#### Backend API (FastAPI)
- [x] POST /targets — create target
- [x] GET /targets — list targets
- [x] GET /targets/{id}/summary — target overview with scoring
- [x] POST /endpoints — create endpoint
- [x] GET /endpoints — list endpoints
- [x] POST /findings — record findings
- [x] GET /findings — list findings
- [x] POST /scans — launch recon pipeline
- [x] GET /digest — high-signal digest
- [x] POST /analysis/endpoint — local + AI endpoint analysis
- [x] GET /attack/decision — attack prioritization and manual test suggestions

#### Database (SQLite)
- [x] Target model with timestamps
- [x] Endpoint model with discovered_at tracking
- [x] Finding model with severity and description
- [x] Automatic schema initialization

#### Storage Layout
- [x] targets/{target_name}/ directory structure
- [x] targets/{target_name}/recon/ for raw tool outputs
- [x] targets/{target_name}/endpoints/ for normalized endpoint JSON
- [x] targets/{target_name}/analysis/ for summary and metadata
- [x] targets/{target_name}/logs/ for scan logs
- [x] Timestamped artifact tracking

### In Progress 🔄

- Scoring engine accuracy validation and weight tuning
- End-to-end workflow testing (create → scan → digest)
- AI analysis integration stability verification
- Dashboard performance and responsiveness

### Not Started (Phase 1) ⭕

- Optional nuclei execution for vulnerability scanning
- Incremental rescanning and differential reporting
- Automated screenshot capture
- Advanced filtering and search in dashboard
- Report draft generation UI
- Scheduled/automated scan workflows

### Known Limitations

- No nuclei integration yet (future enhancement)
- Ollama/AI analysis is optional and gracefully degraded
- Dashboard lacks advanced filtering
- No email notifications or scheduling
- No API authentication/authorization

---

## Phase 2: File Organization & Storage

### Objectives
Implement robust local storage, timestamping, deduplication, and archive rotation.

### Planned Features
- Timestamped outputs with ISO format tracking
- Automatic deduplication by path pattern
- Structured JSON archives
- SearchableS JSON with jq support
- Automatic rotation of old scans (30-day retention)
- Differential reporting (new vs. previously seen)

---

## Phase 3: AI Analysis Integration

### Objectives
Improve Ollama integration for endpoint analysis, auth hypotheses, and report drafting.

### Planned Features
- AI endpoint summarization (concise descriptions)
- Auth flaw hypothesis generation
- Endpoint categorization refinement
- Report draft generation with CWE mapping
- Graceful fallback if Ollama unavailable
- Timeout protection and hallucination prevention

---

## Phase 4: Workflow Automation

### Objectives
Implement practical automation for operator efficiency.

### Planned Features
- Scheduled scans (time-based)
- Overnight recon mode (DEEP with extended timeouts)
- Target rotation queuing
- Auto-digest generation
- Incremental deduplication
- Scan history and versioning
- Comparative analysis across scan runs

---

## Phase 5: Report Assistant

### Objectives
Build an editable report drafting and export system.

### Planned Features
- Report title and summary
- Reproducible step-by-step instructions
- Impact assessment
- CWE/CVSS mapping
- Remediation suggestions
- Export to Markdown, HTML, PDF
- Platform-friendly formatting (HackerOne, Bugcrowd, etc.)

---

## Engineering Principles

**Keep It Practical:**
- No Kubernetes or distributed systems
- No vector databases or embeddings
- No advanced ML pipelines
- SQLite only for persistence
- FastAPI + Streamlit for UI/API

**Avoid Over-Engineering:**
- No microservices unless necessary
- No React migration
- No excessive animations
- No decorative complexity

**Prioritize Signal:**
- Clear scoring with explainable weights
- Deterministic heuristics (not probabilistic)
- Low-noise digest
- Operator-focused UX

---

## Current MVP Status

**Tier 1 (MVP):** ✅ Complete
- Core recon pipeline
- Endpoint parsing and scoring
- Target creation and listing
- Digest generation
- Dashboard with 7 tabs
- Backend API with core routes
- SQLite persistence

**Tier 2 (Hardening):** 🔄 In Progress
- Scoring accuracy validation
- Dashboard performance
- End-to-end workflow validation
- Ollama fallback testing
- Error handling edge cases

**Tier 3 (Enhancement):** ⭕ Planned
- Nuclei integration
- Automated scheduling
- Report drafting
- Advanced filtering
- Archive rotation

---

## Quick Reference: Running Rastro

### Terminal 1: Backend API
```bash
cd /home/adrie/Rastro
./venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2: Dashboard
```bash
cd /home/adrie/Rastro
./venv/bin/streamlit run dashboard/app.py
```

### Typical Workflow
1. Dashboard: Create a new target (e.g., "example.com")
2. Dashboard → Recon tab: Select target and run scan (FAST mode for quick testing)
3. Backend: Runs subfinder, wayback, katana, and normalizes endpoints
4. Dashboard → High Signal: Review high-risk endpoints
5. Dashboard → Findings: Record discovered issues
6. Dashboard → Daily Digest: See summarized high-impact findings

---

## Architecture Notes

**Data Flow:**
```
Target Creation (Dashboard) → SQLite
    ↓
Scan Execution (Backend) → Recon Tools → targets/{name}/recon/
    ↓
Endpoint Parsing → targets/{name}/endpoints/normalized_endpoints.json
    ↓
Scoring & Digest Generation → Analysis output
    ↓
Dashboard Display → Browser
```

**Module Responsibilities:**
- `main.py` — FastAPI routes and orchestration
- `dashboard/app.py` — Streamlit UI and backend integration
- `core/recon/runner.py` — Pipeline orchestration
- `core/recon/parser.py` — Endpoint normalization and deduplication
- `core/scoring/scorer.py` — Heuristic scoring logic
- `core/analysis/analyzer.py` — Endpoint classification
- `database/` — SQLAlchemy models and initialization
- `ai/analysis.py` — Ollama wrapper (optional)

---
