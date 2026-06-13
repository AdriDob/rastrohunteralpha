#!/bin/bash
set -euo pipefail

# Rastro Desktop - Full Build Pipeline (WSL bash)
# Usage: ./scripts/build.sh [--quick] [--step frontend|sync|pyi|deploy|zip|nsis]

QUICK=false
STEP="all"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --quick) QUICK=true; shift ;;
        --step) STEP="$2"; shift 2 ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

PROJECT_WSL="/home/adrie/projects/Rastro"
WSL_PYTHON="/mnt/c/Users/adrie/AppData/Local/Programs/Python/Python312/python.exe"
DESKTOP="/mnt/c/Users/adrie/Desktop"
VERSION="1.0.0-rc1"
SYNC_TAR="_rastro_sync.tar"
WSL_BUILD="/mnt/c/Users/adrie/Rastro-Build"
WSL_PROJECT="/mnt/c/Users/adrie/Rastro-Build/project"
WSL_DIST="/mnt/c/Users/adrie/Rastro-Build/dist"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; GRAY='\033[0;90m'; NC='\033[0m'

do_step() {
    local name="$1" label="$2"; shift 2
    if [[ "$STEP" != "all" && "$STEP" != "$name" ]]; then return; fi
    if [[ "$name" == "nsis" && "$QUICK" == true ]]; then
        echo -e "${YELLOW}  [SKIP] NSIS (--quick)${NC}"; return
    fi
    echo -e "${CYAN}=== $label ===${NC}"
    local sw=$SECONDS
    "$@"
    echo -e "  ${GREEN}[OK] $label ($((SECONDS - sw))s)${NC}"
}

# --- Step functions ---

step_frontend() {
    cd "$PROJECT_WSL/frontend"
    npm run build
}

step_sync() {
    local tar_tmp="/tmp/$SYNC_TAR"
    local tar_dst="$WSL_PROJECT/$SYNC_TAR"

    echo "  Creating tar ($PROJECT_WSL)..."
    cd "$PROJECT_WSL"
    tar cf "$tar_tmp" --exclude=__pycache__ --exclude=*.pyc \
        api core database desktop scripts frontend/dist Rastro.spec main.py

    echo "  Copying to Windows..."
    cp "$tar_tmp" "$tar_dst"

    echo "  Extracting at $WSL_PROJECT..."
    tar xf "$tar_dst" -C "$WSL_PROJECT"

    echo "  Cleaning up..."
    rm -f "$tar_tmp" "$tar_dst"

    echo "  $(find "$WSL_PROJECT" -maxdepth 1 -type f -o -type d | wc -l) entries at destination"
}

step_pyi() {
    cd "$WSL_PROJECT"
    # Use Windows-native paths (not /mnt/c/...) to avoid PyInstaller
    # prepending C:\mnt\c\ to output paths
    "$WSL_PYTHON" -m PyInstaller Rastro.spec --clean -y \
        --distpath "C:/Users/adrie/Rastro-Build/dist" \
        --workpath "C:/Users/adrie/Rastro-Build/build"
}

step_deploy() {
    local dst="$DESKTOP/Rastro"
    rm -rf "$dst"
    mkdir -p "$dst"
    local win_src="C:/Users/adrie/Rastro-Build/dist/Rastro"
    local win_dst="C:/Users/adrie/Desktop/Rastro"
    /mnt/c/Windows/System32/robocopy.exe "$win_src" "$win_dst" /E /COPY:DAT /NP /NDL /NFL /NJH /NJS > /dev/null 2>&1 || true
    local count
    count=$(find "$dst" -type f 2>/dev/null | wc -l)
    echo "  $count files deployed"
}

step_zip() {
    cd "$WSL_PROJECT"
    "$WSL_PYTHON" scripts/package_portable.py \
        --source "C:/Users/adrie/Rastro-Build/dist/Rastro" \
        --output "C:/Users/adrie/Rastro-Build/dist" \
        --version "$VERSION"
}

step_nsis() {
    local makensis
    makensis=$(PATH="/mnt/c/Program Files (x86)/NSIS:/mnt/c/Program Files/NSIS" which makensis.exe 2>/dev/null || true)
    if [[ -z "$makensis" ]]; then
        echo -e "${YELLOW}  [SKIP] NSIS not installed${NC}"
        return
    fi
    cd "$WSL_PROJECT"
    "$makensis" scripts/installer.nsi
}

# --- Run ---

do_step frontend  "Build frontend"       step_frontend
do_step sync      "Sync source files"    step_sync
do_step pyi       "PyInstaller"          step_pyi
do_step zip       "Portable ZIP"         step_zip
do_step deploy    "Copy to Desktop"      step_deploy
do_step nsis      "NSIS Installer"       step_nsis

# --- Summary ---

echo -e "\n${GREEN}=== BUILD COMPLETE ===${NC}"
echo -e "  Desktop: $DESKTOP/Rastro/Rastro.exe"
echo -e "  ZIP:     $WSL_DIST/Rastro-Portable-$VERSION.zip"
if [[ -f "$WSL_DIST/Rastro-Setup-$VERSION.exe" ]]; then
    echo -e "  NSIS:    $WSL_DIST/Rastro-Setup-$VERSION.exe"
fi
echo -e "${GRAY}Validate: curl http://127.0.0.1:8000/api/health${NC}"
