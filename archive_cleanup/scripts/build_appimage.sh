#!/usr/bin/env bash
set -euo pipefail

# ── Build Rastro AppImage (Linux) ──
# Prerequisites:
#   - PyInstaller build completed (scripts/build_linux.sh)
#   - wget available
#
# Usage: bash scripts/build_appimage.sh

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VERSION=$(cat VERSION 2>/dev/null || echo "1.0.0")
ARCH=x86_64

echo "=== Building Rastro AppImage v$VERSION ==="

# 1. Download appimagetool if not cached
APPIMAGETOOL="/tmp/appimagetool"
if [ ! -f "$APPIMAGETOOL" ]; then
  echo "[1/5] Downloading appimagetool..."
  wget -q "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-${ARCH}.AppImage" -O "$APPIMAGETOOL"
  chmod +x "$APPIMAGETOOL"
fi

# 2. Verify PyInstaller dist exists
DIST_DIR="$ROOT/dist/Rastro"
if [ ! -f "$DIST_DIR/Rastro" ]; then
  echo "ERROR: PyInstaller build not found. Run scripts/build_linux.sh first."
  exit 1
fi
echo "[2/5] PyInstaller dist found at $DIST_DIR"

# 3. Create AppDir structure
APPDIR="/tmp/rastro-appimage"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/lib/rastro"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
echo "[3/5] Created AppDir"

cp -r "$DIST_DIR/_internal/"* "$APPDIR/usr/lib/rastro/"
cp "$DIST_DIR/Rastro" "$APPDIR/usr/bin/rastro-bin"

# Generate a purple 256x256 PNG icon using Python
python3 -c "
import struct, zlib
def create_png(w, h, color):
    raw = b''
    for y in range(h):
        raw += b'\\x00'
        for x in range(w):
            raw += bytes(color)
    compressed = zlib.compress(raw)
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)
    return b'\\x89PNG\\r\\n\\x1a\\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')
with open('$APPDIR/usr/share/icons/hicolor/256x256/apps/rastro.png', 'wb') as f:
    f.write(create_png(256, 256, (124, 58, 237)))
"

# Icon symlink for root
ln -sf "usr/share/icons/hicolor/256x256/apps/rastro.png" "$APPDIR/rastro.png"

# AppRun
cat > "$APPDIR/AppRun" << 'EORUN'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
export LD_LIBRARY_PATH="$HERE/usr/lib/rastro:$LD_LIBRARY_PATH"
exec "$HERE/usr/bin/rastro-bin" "$@"
EORUN
chmod +x "$APPDIR/AppRun"

# Desktop file
cat > "$APPDIR/usr/share/applications/rastro.desktop" << 'EODESK'
[Desktop Entry]
Name=Rastro
Comment=Private Investigation Operating System
Exec=rastro-bin
Icon=rastro
Terminal=false
Type=Application
Categories=Utility;Security;
StartupWMClass=Rastro
EODESK
ln -sf "usr/share/applications/rastro.desktop" "$APPDIR/rastro.desktop"

echo "[4/5] Running appimagetool..."
export ARCH=x86_64
"$APPIMAGETOOL" "$APPDIR" "$ROOT/dist/Rastro-${VERSION}-${ARCH}.AppImage"

# Verify
APPIMAGE="$ROOT/dist/Rastro-${VERSION}-${ARCH}.AppImage"
if [ -f "$APPIMAGE" ]; then
  SIZE=$(du -h "$APPIMAGE" | cut -f1)
  echo "[5/5] AppImage: $APPIMAGE ($SIZE)"
else
  echo "ERROR: AppImage not created"
  exit 1
fi

echo ""
echo "=== BUILD COMPLETE ==="
echo "  AppImage: $APPIMAGE"
