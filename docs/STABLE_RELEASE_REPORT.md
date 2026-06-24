# Rastro 1.5.0 — Stable Release Report

**Version:** 1.5.0  
**Type:** stable  
**Date:** 2026-06-20  
**Previous:** 1.5.0-dev

---

## Summary

Rastro 1.5.0-stable consolidates all features and fixes from the 1.5.x development cycle into a hardened, production-ready release. All four major consolidation phases (A–D) are complete, and stability (FASE E) has been hardened with zero known crashes.

**Key achievement:** `generate_from_technology()` and `generate_from_discovered_paths()` are NOW CONNECTED to the production pipeline — no longer dead code. The RewardLearner is NOW WIRED into the report flow — no longer orphaned.

## What's New in 1.5.0

### FASE A — Capability Matrix
- `docs/CAPABILITY_MATRIX.md` — 80+ capabilities classified (✅/⚠️/🔌/❌)

### FASE B — Program Discovery
- `Hunter.fetch_public_programs()` improved: multiple fallback URLs per platform, better JSON key detection, resilient error handling

### FASE C — Hypothesis Engine Connected
- **`generate_from_technology()`** — now reached in production via pipeline technology detection
- **`generate_from_discovered_paths()`** — now reached in production via path extraction from clean endpoints
- `AttackSurfaceMap` expanded with `technologies` and `discovered_paths` fields
- Pipeline auto-detects technologies from TargetIntel + fingerprint_program()
- Pipeline auto-extracts suspicious paths from clean endpoint data

### FASE D — Reward Learning Connected
- **`RewardLearner.analyze()`** — now called on every report update with payout/status changes
- **`GET /api/reports/reward-learning`** — new API endpoint exposing by-type stats, by-program metrics, prediction accuracy
- Fully exported from `core_engines.intelligence`

### FASE E — Stability
- 2 HIGH issues fixed: `App.tsx` searchParams infinite loop, `EVHWidget.tsx` unsafe optional chain
- 0 visible console errors in frontend
- 0 backend crashes

### Zero-Day Pipeline
- Full recon pipeline: subfinder → katana → httpx → fingerprinting → classification → scoring
- Historical URL discovery via gau
- Fuzzing via ffuf (5 profiles: fast/balanced/deep/api/subdomains)

### Intelligence Layer
- Hypothesis Engine with 12 vulnerability generators + technology-aware + discovered-path generators
- Reward Learner tracking per-type/program payout history and prediction accuracy
- Bug bounty intelligence with platform metrics and trend analysis

### Import/Export
- Burp Suite XML/JSON import
- OWASP ZAP XML/JSON import
- HackerOne JSON / Bugcrowd HTML export

## Test Results

```
289 tests collected
289 passed (100%)
0 failed
0 regressions
```

### Module Coverage

| Module | Tests | Status |
|--------|-------|--------|
| Hypothesis generators | 10 | ✅ |
| Reward learning | 6 | ✅ |
| E2E pipeline flow | 12 | ✅ |
| New integrations | 27 | ✅ |
| API endpoints | 44 | ✅ |
| Core engines | 190 | ✅ |

## Known Issues

1. **Windows binary** — Not included; cross-compilation not supported from Linux
2. **Android APK rebuild** — Included as pre-built (Jun 16); Java 21+ needed
3. **RewardLearner persistence** — Adjustments are in-memory only; lost on restart (low severity; target 1.5.1)
4. **Orphan FK deletes** — 19 ForeignKeys without `ondelete`; application-level cleanup works
5. **Service worker 404** — `/service-worker.js` registered but not found in project (cosmetic; low severity)

## Build Details

**Environment:**
- Python 3.14.4
- Node.js (Vite build)
- Linux x86_64
- SQLite (single-file database)

**Artifacts:**
```
dist/Rastro-1.5.0-stable.zip          94 MB  360 files
dist/Rastro-1.5.0-stable-manifest.json 72 KB
dist/Rastro-1.5.0-stable-checksums.sha256  47 KB
```

**Archive Structure:**
```
Rastro-1.5.0-stable/
├── Android/
│   └── rastro-android-debug.apk      4.2 MB
├── Linux/
│   └── Rastro/
│       ├── Rastro (binary)          21 MB
│       └── _internal/
├── docs/
│   ├── CAPABILITY_MATRIX.md         NEW
│   ├── CHANGELOG.md
│   ├── FINAL_CHECKLIST.md
│   ├── README.md
│   ├── STABLE_RELEASE_REPORT.md
│   ├── VALIDATION_REPORT.md
│   └── VERSION
└── config/
    └── Rastro.spec
```

## Release Artifacts

| File | SHA256 (first 16 chars) |
|------|-------------------------|
| Rastro-1.5.0-stable.zip | ebe3f056... |
| rastro-android-debug.apk | 413768a6... |

All checksums verified against `Rastro-1.5.0-stable-checksums.sha256`.
