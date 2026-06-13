# Android Build Guide

Rastro frontend is a React + Vite app that can be packaged as an Android APK
via Capacitor (https://capacitorjs.com).

## Prerequisites

- Node.js 18+
- Android Studio (for SDK + emulator)
- Java 17+
- A physical Android device or emulator

## Build Steps

```bash
# 1. Install Capacitor CLI
npm install -g @capacitor/cli @capacitor/core

# 2. Build the frontend
cd frontend
npm ci
npm run build

# 3. Initialize Capacitor (first time only)
npx cap init Rastro com.rastro.app --webDir dist

# 4. Add Android platform
npx cap add android

# 5. Copy web build into native project
npx cap copy android

# 6. Open Android Studio
npx cap open android

# 7. In Android Studio: Build → Build Bundle(s) / APK → Build APK
#    Output: android/app/build/outputs/apk/debug/app-debug.apk
```

## Development

For live reload during development:
```bash
# Start Vite dev server
cd frontend && npm run dev

# In another terminal, point Capacitor to dev server
npx cap copy android
npx cap open android
# Then run from Android Studio
```

## Notes

- The Android app is a webview wrapper around the Rastro frontend.
- Backend must be running on a reachable server (localhost or remote).
- Configure the API URL in frontend/src/lib/api.ts (BASE constant).
- For production, sign the APK with a release keystore.
