#!/bin/bash
set -euo pipefail

ROOT="$(dirname "$0")/.."
cd "$ROOT"

echo "=== Rastro — Linux Build ==="

# 1. Frontend
echo "→ Building frontend..."
cd frontend
npm install --silent
npm run build
cd ..

# 2. PyInstaller
echo "→ Packaging desktop binary..."
pyinstaller Rastro.spec -y

echo "✓ Linux build complete: $(pwd)/dist/Rastro/"
ls -lh dist/Rastro/Rastro
