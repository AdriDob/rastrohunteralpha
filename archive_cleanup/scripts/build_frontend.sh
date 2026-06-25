#!/bin/bash
set -euo pipefail

echo "=== Rastro — Frontend Build ==="
cd "$(dirname "$0")/../frontend"
npm install --silent
npm run build
echo "✓ Frontend build: $(pwd)/dist"
