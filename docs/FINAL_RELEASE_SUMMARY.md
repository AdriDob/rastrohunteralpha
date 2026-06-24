# Rastro 1.5.0 — FINAL RELEASE SUMMARY

**Date:** 2026-06-20  
**Version:** 1.5.0-stable-final  
**Release Type:** STABLE

---

## Test Results

| Metric | Value |
|--------|-------|
| Total tests | 289 |
| Passed | **289 (100%)** |
| Failed | 0 |
| Regressions | 0 |
| E2E pipeline tests | 12/12 passing |
| TypeScript errors | 0 |
| Frontend build | Clean (562+ modules) |

## Bugs Corrected (this consolidation)

| # | Issue | Severity | Fix |
|---|-------|----------|-----|
| 1 | `generate_from_technology()` dead code | HIGH | Connected through pipeline (FASE C) |
| 2 | `generate_from_discovered_paths()` dead code | HIGH | Connected through pipeline (FASE C) |
| 3 | `RewardLearner.analyze()` never called | HIGH | Wired into report update flow (FASE D) |
| 4 | `App.tsx` searchParams infinite loop | HIGH | Changed to `[]` deps |
| 5 | `EVHWidget.tsx` unsafe optional chain | HIGH | Added `?.` guard |
| 6 | Hunter.fetch_public_programs() single-endpoint | MEDIUM | Multiple fallback URLs per platform |
| 7 | RewardLearner not exported from package | MEDIUM | Added to `__init__.py` |
| 8 | No reward learning API endpoint | MEDIUM | `GET /api/reports/reward-learning` created |
| 9 | AttackSurfaceMap missing tech/path fields | MEDIUM | Added `technologies`, `discovered_paths` |
| 10 | AttackSurfaceArtifact missing fields | LOW | Added matching fields |

## Coverage

| Phase | Description | Status |
|-------|-------------|--------|
| A | CAPABILITY_MATRIX.md | ✅ 80+ capabilities classified |
| B | Program discovery improved | ✅ Multi-URL fallback, better key detection |
| C | Hypothesis → production pipeline | ✅ Technologies + discovered paths now flow through |
| D | RewardLearner → report flow | ✅ Called on payout/status update, API exposed |
| E | Frontend stability | ✅ 2 HIGH fixed, 0 visible console errors |

## Artifacts Generated

| Artifact | Size | SHA256 (first 16) |
|----------|------|-------------------|
| `Rastro-1.5.0-stable.zip` | 94 MB (361 files) | `a0fa374a81169768` |
| `rastro-android-debug.apk` | 4.2 MB | `413768a60af2cd52` |
| `Rastro-1.5.0-stable-checksums.sha256` | 48 KB | `—` |
| `Rastro-1.5.0-stable-manifest.json` | 72 KB | `—` |

## Final Hashes (Key Files)

```
a0fa374a811697689cc01a35b3cfa47c72114897c200447354ea255da3f08a20  Rastro-1.5.0-stable.zip
413768a60af2cd52c5f3a3ef6ef8ecc76a962e6dfe2f5e2d512a3407de5e37fb  rastro-android-debug.apk
3ac5faf9b50a531dcf0a7cddfd4264a75d75bbbe83e6ce648bf027f7f7771fb0  docs/CAPABILITY_MATRIX.md
9db3c77524e06dec6a14720f92ddf13c5462339a8ed8370d3e544556e15f73b9  docs/VALIDATION_REPORT.md
953c30b26f041d93897cc56378e75e74939a72c474c63dd3564fbf4fff9f9d6c  docs/FINAL_CHECKLIST.md
9aba7ce969a83de22663ffa94145f3b9a0c0819675f560ac234ab890c719c88d  docs/STABLE_RELEASE_REPORT.md
```

## ZIP Structure

```
Rastro-1.5.0-stable/
├── Android/          ✅ rastro-android-debug.apk
├── Linux/
│   └── Rastro/       ✅ binary + _internal/ (360 deps)
├── docs/
│   ├── CAPABILITY_MATRIX.md       NEW
│   ├── CHANGELOG.md
│   ├── FINAL_CHECKLIST.md         UPDATED
│   ├── README.md
│   ├── STABLE_RELEASE_REPORT.md   UPDATED
│   ├── VALIDATION_REPORT.md       UPDATED
│   └── VERSION
├── config/
│   └── Rastro.spec
└── VERSION
```

## Stability Status

| Criterion | Status |
|-----------|--------|
| 0 crashes | ✅ |
| 0 visible console errors | ✅ |
| 0 backend exceptions | ✅ |
| 289 tests passing | ✅ |
| All phases (A–E) complete | ✅ |
| ZIP integrity verified | ✅ |
| OneDrive delivery | ✅ |

## Post-Release (v1.5.1 / v1.6.0)

1. **Windows build** — requires Windows host or cross-compilation setup
2. **Android APK rebuild** — needs Java 21 JDK
3. **RewardLearner persistence** — save adjustments to DB (in-memory only now)
4. **Reward learning dashboard widget** — frontend UI for reward learning data
5. **Orphan FK deletes** — add `ondelete` to 19 ForeignKeys
6. **Granular error boundaries** — per-page ErrorBoundary components
7. **Correlation engine** — wire `EndpointCorrelator` into pipeline
