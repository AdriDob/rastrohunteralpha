# Authentication Audit

## Token Lifecycle

| Stage | Behavior | Status |
|-------|----------|--------|
| First launch (no token) | `onRehydrateStorage` → no token in URL → `getOverview()` → 401 → token cleared → error shown gracefully | ✅ No redirect loop |
| URL token present | Token extracted by `onRehydrateStorage` via `URLSearchParams`, stored via `setAuthToken()` before first API call | ✅ Token stored pre-fetch |
| Normal operation | All API calls include `Authorization: Bearer <token>` header, 401 clears token without page reload | ✅ Proper error handling |
| Invalid/expired token | 401 response → `sessionStorage.removeItem('rastro-token')` → error thrown → component renders error state | ✅ No infinite loop |

## Fixes Applied

### 1. `frontend/src/stores/index.ts` (onRehydrateStorage)
**Problem:** `getOverview()` was called before extracting the token from URL, causing a 401 that triggered a full page reload loop.

**Fix:** Token extraction (`new URLSearchParams(...).get('token')`) and `setAuthToken()` moved **before** `getOverview()`.

**Code path:**
```
onRehydrateStorage
  → extract token from URL
  → setAuthToken(urlToken)          // NEW: before API call
  → await getOverview()             // now has valid token
  → dashboard loads successfully
```

### 2. `frontend/src/lib/api.ts` (401 handler)
**Problem:** `window.location.href = '/'` caused full page reload → token lost → 401 loop.

**Fix:** 401 handler now only calls `sessionStorage.removeItem('rastro-token')` and throws an error. No navigation.

### 3. `frontend/src/App.tsx` (onboarding detection)
**Problem:** `onboarding=1` URL param took priority over `localStorage` completion flag, re-showing onboarding on every launch.

**Fix:** `localStorage.getItem('rastro-onboarding-complete')` checked first; URL param only used if localStorage flag is absent.

## Desired Behavior

1. First launch: user gets token via URL → dashboard loads → onboarding shown if `?onboarding=1` → user completes onboarding → flag stored in localStorage
2. Subsequent launches: localStorage flag found → onboarding skipped → dashboard loads immediately
3. Token expires: 401 → error state shown → no redirect loop → user can manually re-authenticate
4. Invalid URL: no token → `getOverview()` 401 → graceful error → no crash

## Verification Method

- Code review: all three fix locations confirmed
- Logic trace: no code path leads to `window.location.href = '/'` in 401 scenario
- Token timing: `setAuthToken()` executed synchronously before `await getOverview()` in `onRehydrateStorage`

**Status: PASS (code review)**
