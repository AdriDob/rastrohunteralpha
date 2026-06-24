# Rastro 1.5.0 — Final Release Checklist

**Date:** 2026-06-20  
**Version:** 1.5.0-stable

---

## Quality Gates

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | Python test suite (full) | ✅ 289/289 pass | 0 failures |
| 2 | TypeScript typecheck | ✅ 0 errors | `npx tsc --noEmit` clean |
| 3 | Frontend Vite build | ✅ Clean | 562+ modules bundled |
| 4 | Backend starts cleanly | ✅ | No warnings on boot |
| 5 | API health endpoint | ✅ | Returns `{"status": "ok"}` |
| 6 | Target CRUD | ✅ | Create, read, list, detail |
| 7 | Endpoint CRUD | ✅ | Create, list by target |
| 8 | Finding CRUD | ✅ | Create, persist |
| 9 | Report CRUD | ✅ | Create from findings, list |
| 10 | DB persistence | ✅ | Data survives session close/reopen |

## FASE A — Capability Matrix

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | `docs/CAPABILITY_MATRIX.md` | ✅ Generated — 80+ capabilities classified across 15 categories |

## FASE B — Program Discovery

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | Hunter improved with fallback URLs | ✅ | Multiple endpoints per platform |
| 2 | Better JSON key detection | ✅ | Handles `programs`, `results`, `data`, `items`, `rows` |
| 3 | Graceful failure on auth | ✅ | Returns empty list, no crash |

## FASE C — Hypothesis Connection

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | `AttackSurfaceMap.technologies` field added | ✅ | Default `[]` |
| 2 | `AttackSurfaceMap.discovered_paths` field added | ✅ | Default `[]` |
| 3 | `AttackSurfaceMapper.map()` accepts params | ✅ | Optional `technologies`, `discovered_paths` |
| 4 | Pipeline detects technologies from intel + fingerprint | ✅ | `_detect_technologies()` queries DB + `fingerprint_program()` |
| 5 | Pipeline extracts discovered paths from endpoints | ✅ | `_extract_discovered_paths()` — 15 patterns |
| 6 | Both flow to HypothesisEngine | ✅ | Through `vars(surface_map)` |
| 7 | `generate_from_technology()` called in production | ✅ | Verified — no longer dead code |
| 8 | `generate_from_discovered_paths()` called in production | ✅ | Verified — no longer dead code |
| 9 | `AttackSurfaceArtifact` updated | ✅ | Matching fields added |

## FASE D — Reward Learning Connected

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | `RewardLearner` exported from package | ✅ | `core_engines.intelligence` |
| 2 | API endpoint `GET /api/reports/reward-learning` | ✅ | Returns by-type, by-program, prediction accuracy |
| 3 | Called on report update | ✅ | When `confirmed_reward` or `status` changes |
| 4 | Adjustments available via `get_adjustments()` | ✅ | Per-type payout factors |

## FASE E — Stability

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | `App.tsx` searchParams infinite loop | HIGH | ✅ Fixed |
| 2 | `EVHWidget.tsx` unsafe optional chain | HIGH | ✅ Fixed |
| 3 | TaskQueue useEffect deps | MEDIUM | ⚠️ Noted (intentional) |
| 4 | setState after unmount (8 components) | MEDIUM | ⚠️ Noted (no crashes) |
| 5 | IdentityVaultWidget loading state | LOW | ⚠️ Noted |
| 6 | Service worker 404 | LOW | ⚠️ Noted |

## Build Artifacts

| Artifact | Path | Size |
|----------|------|------|
| Release ZIP | `dist/Rastro-1.5.0-stable.zip` | 94 MB (360 files) |
| Manifest | `dist/Rastro-1.5.0-stable-manifest.json` | 72 KB |
| Checksums | `dist/Rastro-1.5.0-stable-checksums.sha256` | 47 KB |
| Android APK | `dist/rastro-android-debug.apk` | 4.2 MB |

## Required but Blocked

| Item | Reason | Status |
|------|--------|--------|
| Windows desktop build | Cross-compile not supported from Linux | ⚠️ Blocked |
| Android APK rebuild | Java 21 JDK not available | ⚠️ Pre-built APK included |

## Sign-off

| Role | Name | Date |
|------|------|------|
| Build | Automated | 2026-06-20 |
| Validation | Automated (CI) | 2026-06-20 |
| Release | — | — |
