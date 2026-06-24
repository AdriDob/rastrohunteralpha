# Packaged Release Validation

## Windows EXE: `Rastro.exe`

### Build Details
- **Builder:** Windows Python 3.12.10 via WSL2 interop
- **PyInstaller:** 6.20.0
- **Type:** `--onedir` (directory with `_internal/`)
- **Entry point:** `desktop/main_desktop.py`
- **Frontend:** Fresh `npm run build` included as data
- **File type:** PE32+ executable, console, x86-64

### Validation on Real Windows
The EXE must be validated on an actual Windows machine by:

1. **Installation check:** Copy `Rastro.exe` + `_internal/` to a clean Windows directory
2. **First launch:** Run `Rastro.exe` from command prompt to see console output
3. **Startup crash check:** Verify no `TypeError`, `KeyError`, or `ModuleNotFoundError` on startup
4. **Dashboard load:** Verify MissionControl page renders fully
5. **Auth flow:** Verify no "Authenticating session" loop, no 401 loop
6. **Onboarding:** On first run with `?onboarding=1`, verify wizard appears; on subsequent runs, verify it does not
7. **Close/reopen:** Close app, reopen, verify no crash, dashboard loads immediately

### Known Warnings (non-blocking)
- Hidden imports `pycparser.lextab`, `pycparser.yacctab` not found (false positives from cryptography hooks)
- Hidden imports `pysqlite2`, `MySQLdb` not found (optional DB drivers, SQLite fallback used)
- Hidden import `mx.DateTime` not found (false positive from SQLAlchemy hooks)

### File Checksums
```
SHA256(Rastro.exe) = <computed at packaging time>
```
**Status: BUILT — requires Windows runtime validation**

## Android APK: `Rastro-debug.apk`

### Build Details
- **Builder:** WSL2 Ubuntu with JDK 21.0.11 (Temurin)
- **Android SDK:** `~/Android/Sdk`
- **Capacitor:** 8.x (sync with `npx cap sync android`)
- **Build tools:** Android Gradle Plugin 8.13.0, Gradle 8.14.3
- **Frontend:** Fresh `npm run build` included via Capacitor sync

### Validation on Real Device/Emulator

1. **Installation:** `adb install Rastro-debug.apk` (or drag-drop onto emulator)
2. **Native behavior:** App should open from icon as native app, no external browser redirect
3. **Auth flow:** Enter license key → should receive token → dashboard loads
4. **Portrait mode:** All 8 screens render without clipped/hidden content
5. **Landscape mode:** Same screens rotate correctly
6. **Tablet/foldable:** Responsive layouts adapt (768px breakpoint)
7. **Back navigation:** Android back button works correctly

### Screens Validated for Responsiveness
- MissionControl (`flexWrap` header)
- FindingsPipeline (2-col KPI grid on mobile, 100% select width)
- ReportCenter (single-col KPI grid, `flexWrap` buttons)
- OpportunityRadar (`flexWrap` header)
- ReportHistory (auto-wrapping grid)
- EvidenceCenter (uses `useIsMobile` hook)
- Settings (single-column layout)
- ProgramCatalog (`flexWrap` toolbar)

**Status: BUILT — requires device/emulator runtime validation**
