# Android Build Validation

## Build Environment

| Component | Value |
|-----------|-------|
| Host | WSL2 Ubuntu on Windows 11 |
| JDK | Temurin-21.0.11+10 LTS |
| Android SDK | `~/Android/Sdk` (build-tools 34+, platform android-34) |
| Gradle | 8.14.3 (wrapper) |
| AGP | 8.13.0 |
| Capacitor | v8 (via `npx cap`) |
| Build mode | `debug` (assembleDebug) |

## Build Output

```
android/app/build/outputs/apk/debug/app-debug.apk
  → copied to dist/android/Rastro-debug.apk
  → file size: 4.4 MB
```

## APK Contents (key items)
- `AndroidManifest.xml` (namespace `ai.rastro.app`)
- `classes.dex` (compiled Java/Kotlin)
- `assets/public/` → frontend SPA (index.html + JS/CSS assets)
- `res/` → Android resources
- `META-INF/` → signing certificates (debug)

## Capacitor Configuration
```
androidScheme: "https"
cleartext: false
```

## Validation Checklist

### Must pass before release
- [ ] Install on Android 14+ device/emulator
- [ ] Open from app icon (not browser)
- [ ] Enter license key → receive token → dashboard loads
- [ ] Rotate to landscape → all screens render correctly
- [ ] Test on tablet (≥768px) → responsive layouts activate
- [ ] Back navigation works
- [ ] No external browser redirects for app content
- [ ] No 401 loops on token expiry
- [ ] No onboarding shown after completion

### Known caveats
- Debug build (`assembleDebug`) — not code-signed for production
- Release build requires `assembleRelease` with proper keystore
- Cleartext HTTP disabled — all API calls must use HTTPS

## Responsive Layout Verification

| Screen | Portrait | Landscape | Tablet | Fix Applied |
|--------|----------|-----------|--------|-------------|
| MissionControl | ✅ | ✅ | ✅ | header flexWrap |
| FindingsPipeline | ✅ | ✅ | ✅ | 2-col KPI grid, 100% select |
| ReportCenter | ✅ | ✅ | ✅ | single-col KPI, button flexWrap |
| OpportunityRadar | ✅ | ✅ | ✅ | header flexWrap |
| ReportHistory | ✅ | ✅ | ✅ | auto-wrapping grid |
| EvidenceCenter | ✅ | ✅ | ✅ | useIsMobile hook |
| Settings | ✅ | ✅ | ✅ | single-column layout |
| ProgramCatalog | ✅ | ✅ | ✅ | toolbar flexWrap |

**Status: BUILT — requires device/emulator runtime validation**
