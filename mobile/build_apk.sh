#!/usr/bin/env bash
# Build Rastro Android APK via Capacitor
#
# Usage:
#   ./mobile/build_apk.sh                  # Debug APK
#   ./mobile/build_apk.sh --release        # Release APK (requires keystore)
#   ./mobile/build_apk.sh --clean          # Clean + rebuild
#
# Prerequisites:
#   - Node.js 18+, npm
#   - Java 17 or 21 (JDK)
#   - Android SDK (can be auto-downloaded with --install-sdk)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_DIR/frontend"
ANDROID_DIR="$PROJECT_DIR/android"

MODE="debug"
CLEAN=false
RELEASE=false
INSTALL_SDK=false

for arg in "$@"; do
  case "$arg" in
    --release) RELEASE=true; MODE="release" ;;
    --clean)   CLEAN=true ;;
    --install-sdk) INSTALL_SDK=true ;;
    *) echo "Unknown option: $arg"; exit 1 ;;
  esac
done

# ── Java version check ──────────────────────────────────────────
JAVA_VER=$(java -version 2>&1 | head -1 | grep -oP '\d+' | head -1)
if [ -z "$JAVA_VER" ] || [ "$JAVA_VER" -lt 17 ] || [ "$JAVA_VER" -gt 21 ]; then
  echo "ERROR: Java 17-21 required (detected: v${JAVA_VER:-none})"
  echo ""
  echo "  Quick install with SDKMAN:"
  echo "    curl -s 'https://get.sdkman.io' | bash"
  echo "    sdk install java 21.0.8-tem"
  echo "    sdk use java 21.0.8-tem"
  exit 1
fi
echo "✓ Java $JAVA_VER"

# ── Android SDK check ───────────────────────────────────────────
if [ -z "${ANDROID_HOME:-}" ]; then
  # Common default locations
  for dir in "$HOME/Android/Sdk" "/usr/lib/android-sdk" "/opt/android-sdk"; do
    if [ -d "$dir" ]; then
      export ANDROID_HOME="$dir"
      break
    fi
  done
fi

if [ -z "${ANDROID_HOME:-}" ] || [ ! -d "$ANDROID_HOME" ]; then
  if [ "$INSTALL_SDK" = true ]; then
    echo ""
    echo ">>> Installing Android SDK commandline tools..."
    SDK_URL="https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
    SDK_DIR="$HOME/Android/Sdk"
    mkdir -p "$SDK_DIR"
    cd /tmp
    curl -sL "$SDK_URL" -o cmdline-tools.zip
    unzip -q cmdline-tools.zip
    mkdir -p "$SDK_DIR/cmdline-tools"
    mv cmdline-tools "$SDK_DIR/cmdline-tools/latest"
    export ANDROID_HOME="$SDK_DIR"
    export ANDROID_SDK_ROOT="$SDK_DIR"
    echo "✓ Android SDK installed at $SDK_DIR"

    echo ">>> Installing platform SDK 34 + build tools..."
    yes | "$SDK_DIR/cmdline-tools/latest/bin/sdkmanager" --sdk_root="$SDK_DIR" \
      "platforms;android-34" "build-tools;34.0.0" 2>&1 | tail -5
  else
    echo "ERROR: Android SDK not found. Set ANDROID_HOME or use --install-sdk"
    echo "  export ANDROID_HOME=\$HOME/Android/Sdk"
    echo "  or: ./mobile/build_apk.sh --install-sdk"
    exit 1
  fi
fi
echo "✓ Android SDK: $ANDROID_HOME"

# Write local.properties for Gradle
echo "sdk.dir=$ANDROID_HOME" > "$ANDROID_DIR/local.properties"

echo ""
echo "=== Rastro Android APK Build ($MODE) ==="

# Step 1: Build frontend
echo ""
echo ">>> Building frontend..."
cd "$FRONTEND_DIR"
npm install --silent
npm run build
echo "Frontend built: $FRONTEND_DIR/dist/"

# Step 2: Sync Capacitor
echo ""
echo ">>> Syncing Capacitor..."
cd "$PROJECT_DIR"
npx cap sync android

if [ "$CLEAN" = true ]; then
  echo ""
  echo ">>> Cleaning Android project..."
  cd "$ANDROID_DIR"
  if [ -f "./gradlew" ]; then
    ./gradlew clean
  else
    gradle clean
  fi
fi

# Step 3: Build APK
echo ""
echo ">>> Building APK (this may take a while)..."
cd "$ANDROID_DIR"

BUILD_CMD="./gradlew"
if [ ! -f "./gradlew" ]; then
  BUILD_CMD="gradle"
fi

if [ "$RELEASE" = true ]; then
  $BUILD_CMD assembleRelease
  APK_PATH="app/build/outputs/apk/release/app-release.apk"
else
  $BUILD_CMD assembleDebug
  APK_PATH="app/build/outputs/apk/debug/app-debug.apk"
fi

echo ""
echo "=== Build complete ==="

if [ -f "$APK_PATH" ]; then
  APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
  echo "APK: $APK_PATH ($APK_SIZE)"
  cp "$APK_PATH" "$PROJECT_DIR/dist/rastro-android-debug.apk" 2>/dev/null || true
else
  echo "APK not found at expected path: $APK_PATH"
  echo "Check android/app/build/outputs/apk/"
fi
