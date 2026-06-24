# Startup Flow Audit

## Entry Points

### Desktop (PyInstaller EXE)
Entry point: `desktop/main_desktop.py`

Startup sequence:
```
main()
  → _setup_boot()
  → _setup_logging()
  → set webview window properties
  → start backend (in-process uvicorn on random port)
  → wait for healthy signal
  → _open_browser(ctx) → webview.create_window() loads frontend URL
  → _create_tray() (optional, non-blocking)
  → _event_loop() runs until shutdown
```

### Frontend (React SPA)
Entry point: `frontend/src/main.tsx` → `<App />`

Startup sequence:
```
App
  → QueryClientProvider
  → check onboarding localStorage flag → URL param
  → onRehydrateStorage
      → extract token from URL
      → setAuthToken
      → getOverview()
  → Router renders:
      → showOnboarding ? WelcomeWizard : <Routes>
```

## Error Scenarios

| Scenario | Expected Behavior | Status |
|----------|-------------------|--------|
| No token in URL | `getOverview()` → 401 → error state, no redirect | ✅ |
| Invalid token | 401 → token cleared → error state | ✅ |
| Backend not ready | Frontend shows loading spinner → eventually error | ✅ |
| Backend crashes | WebView shows connection error | ✅ |
| `open_dashboard()` param mismatch | PyInstaller spec using `run.py` → `browser_opener.py` has `onboarding: bool = False` param | ✅ |

## Onboarding Flow

1. `App.tsx:156-160` checks localStorage `rastro-onboarding-complete`
2. If not found, checks `?onboarding=1` URL param
3. If param present, `showOnboarding = true` → renders `WelcomeWizard` component
4. User completes wizard → `localStorage.setItem('rastro-onboarding-complete', 'true')`
5. On next launch, localStorage flag found → onboarding skipped

## PyInstaller Build Verification

- Fresh frontend build (`npm run build`) included: ✅ (tsc + vite pass)
- All hidden imports declared: ✅ (uvicorn, httpx, anyio, pydantic, etc.)
- Frontend dist included as `--add-data`: ✅
- No stale cached builds: ✅ (fresh build with JDK 21 on Android, Windows Python PyInstaller for EXE)

**Status: PASS**
