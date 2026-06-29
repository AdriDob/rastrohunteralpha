#Requires -Version 5.1
<#
.SYNOPSIS
    ORION Windows Release Pipeline — build, test, and generate release report.
.DESCRIPTION
    One-command release pipeline for Windows 11. Run from the repo root:
        PowerShell -ExecutionPolicy Bypass -File scripts/build_windows.ps1

    Executes the full Release Isolation Pipeline:
      1. Clean build (frontend + PyInstaller + NSIS installer)
      2. Import audit
      3. Asset validation
      4. Smoke test (Orion.exe)
      5. Portable test (temp isolation)
      6. Installer test (install + uninstall)
      7. Generate RELEASE_REPORT.md

    Outputs:
        build/release/                  # Staged release artifacts
            Orion/Orion.exe            # PyInstaller one-dir bundle
            OrionInstaller.exe          # NSIS installer
            Orion-<version>.zip         # Portable ZIP
            build_info.json             # Build metadata + SHA256
            README.txt, CHANGELOG.md, VERSION.txt, LICENSE.txt

        RELEASE_REPORT.md               # Full validation report

    Requires: Python 3.12+, Node.js 20+, NSIS 3.0+
    Run from repository root (not from scripts/)
#>

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $ROOT

$GOLD   = "Yellow"
$CYAN   = "Cyan"
$GREEN  = "Green"
$RED    = "Red"
$WHITE  = "White"

Write-Host "╔═══════════════════════════════════════════════╗" -ForegroundColor $GOLD
Write-Host "║        ORION  RELEASE ISOLATION  v1.6        ║" -ForegroundColor $GOLD
Write-Host "╚═══════════════════════════════════════════════╝" -ForegroundColor $GOLD

# ── 1. Check prerequisites ──────────────────────────────────────────
Write-Host "`n[1/6] Checking prerequisites..." -ForegroundColor $CYAN
$missing = @()
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { $missing += "Python 3.12+" }
if (-not (Get-Command node -ErrorAction SilentlyContinue))   { $missing += "Node.js 20+" }
if ($missing.Count -gt 0) {
    Write-Host "  ✗ Missing: $($missing -join ', ')" -ForegroundColor $RED
    exit 1
}

# Check for makensis
$hasMakensis = $true
if (-not (Get-Command makensis -ErrorAction SilentlyContinue)) {
    Write-Host "  ⚠ makensis not found — NSIS installer will be skipped" -ForegroundColor $GOLD
    $hasMakensis = $false
}
Write-Host "  ✓ All prerequisites found" -ForegroundColor $GREEN

# ── 2. Install dependencies ────────────────────────────────────────
Write-Host "`n[2/6] Installing dependencies..." -ForegroundColor $CYAN
pip install -r requirements.txt --quiet
pip install pyinstaller --quiet
Push-Location (Join-Path $ROOT "frontend")
npm ci --silent
Pop-Location
Write-Host "  ✓ Dependencies installed" -ForegroundColor $GREEN

# ── 3. Release Isolation Pipeline ──────────────────────────────────
Write-Host "`n[3/6] Running Release Isolation Pipeline..." -ForegroundColor $CYAN
Write-Host "  (clean build → audit → validate → smoke → portable → installer → report)" -ForegroundColor $WHITE

# Build the NSIS installer flag
$nsisFlag = if ($hasMakensis) { "" } else { "--skip-installer" }

# Run the full pipeline
python scripts/release_isolation.py --clean $nsisFlag
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n  ✗ RELEASE ISOLATION FAILED — see errors above" -ForegroundColor $RED
    Write-Host "  Run each phase individually to debug:" -ForegroundColor $WHITE
    Write-Host "    python scripts/build_release.py --clean" -ForegroundColor $CYAN
    Write-Host "    python scripts/audit_imports.py" -ForegroundColor $CYAN
    Write-Host "    python scripts/validate_assets.py" -ForegroundColor $CYAN
    Write-Host "    python scripts/smoke_test.py" -ForegroundColor $CYAN
    Write-Host "    python scripts/test_portable.py" -ForegroundColor $CYAN
    Write-Host "    python scripts/test_installer.py" -ForegroundColor $CYAN
    exit 1
}

# ── 4. Assemble output ─────────────────────────────────────────────
Write-Host "`n[4/6] Assembling final output..." -ForegroundColor $CYAN
python scripts/assemble_output.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ⚠ Output assembly had issues (non-fatal)" -ForegroundColor $GOLD
}

# ── 5. Verify RELEASE_REPORT.md ────────────────────────────────────
Write-Host "`n[5/6] Verifying release report..." -ForegroundColor $CYAN
$reportPath = Join-Path $ROOT "RELEASE_REPORT.md"
if (Test-Path $reportPath) {
    $reportSize = (Get-Item $reportPath).Length / 1KB
    Write-Host "  ✓ RELEASE_REPORT.md ($('{0:N1}' -f $reportSize) KB)" -ForegroundColor $GREEN
} else {
    Write-Host "  ✗ RELEASE_REPORT.md not generated" -ForegroundColor $RED
    exit 1
}

# ── 6. Summary ─────────────────────────────────────────────────────
Write-Host "`n[6/6] Summary" -ForegroundColor $CYAN
$distDir = Join-Path $ROOT "dist" "Orion"
$distSize = if (Test-Path $distDir) {
    (Get-ChildItem $distDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
} else { 0 }

$releaseDir = Join-Path $ROOT "build" "release"
$releaseSize = if (Test-Path $releaseDir) {
    (Get-ChildItem $releaseDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
} else { 0 }

Write-Host "`n╔═══════════════════════════════════════════════╗" -ForegroundColor $GOLD
Write-Host "║         RELEASE ISOLATION COMPLETE           ║" -ForegroundColor $GOLD
Write-Host "╚═══════════════════════════════════════════════╝" -ForegroundColor $GOLD
Write-Host "  EXE bundle: $distDir ($('{0:N1}' -f $distSize) MB)" -ForegroundColor $WHITE
Write-Host "  Release:    $releaseDir ($('{0:N1}' -f $releaseSize) MB)" -ForegroundColor $WHITE
Write-Host "  Report:     $reportPath" -ForegroundColor $WHITE
$installerPath = Join-Path $ROOT "dist" "OrionInstaller.exe"
if (Test-Path $installerPath) {
    $isize = (Get-Item $installerPath).Length / 1MB
    Write-Host "  Installer:  $installerPath ($('{0:N1}' -f $isize) MB)" -ForegroundColor $WHITE
}
Write-Host ""
Write-Host "  ✓ All tests passed — ready for release" -ForegroundColor $GREEN
Write-Host "  Report: $reportPath" -ForegroundColor $CYAN
