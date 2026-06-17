#Requires -Version 5.1
<#
.SYNOPSIS
    Build Rastro Windows executable (.exe) via PyInstaller.
.DESCRIPTION
    One-command build for Windows 11. Run from the repo root:
        PowerShell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
    Produces: dist/Rastro/Rastro.exe
.NOTES
    Requires: Python 3.12+, Node.js 20+, Git
#>

$ErrorActionPreference = "Stop"
$ROOT = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $ROOT
Write-Host "=== Building Rastro for Windows ===" -ForegroundColor Cyan

# ── 1. Check prerequisites ──────────────────────────────────────────
$missing = @()
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { $missing += "Python 3.12+" }
if (-not (Get-Command node -ErrorAction SilentlyContinue))   { $missing += "Node.js 20+" }
if ($missing.Count -gt 0) {
    Write-Host "Missing prerequisites: $($missing -join ', ')" -ForegroundColor Red
    exit 1
}

# ── 2. Install Python dependencies ──────────────────────────────────
Write-Host "`n[1/5] Installing Python dependencies..." -ForegroundColor Green
pip install -r requirements.txt
pip install pyinstaller

# ── 3. Build frontend ───────────────────────────────────────────────
Write-Host "`n[2/5] Building frontend..." -ForegroundColor Green
Set-Location (Join-Path $ROOT "frontend")
npm ci
npm run build
Set-Location $ROOT

# ── 4. PyInstaller build ────────────────────────────────────────────
Write-Host "`n[3/5] Building executable (PyInstaller)..." -ForegroundColor Green
pyinstaller Rastro.spec -y

# ── 5. Verify output ────────────────────────────────────────────────
$exe = Join-Path $ROOT "dist" "Rastro" "Rastro.exe"
if (-not (Test-Path $exe)) {
    Write-Host "ERROR: $exe not found" -ForegroundColor Red
    exit 1
}
$size = (Get-Item $exe).Length / 1MB
Write-Host "`n[4/5] ✓ Rastro.exe generated ($('{0:N1}' -f $size) MB)" -ForegroundColor Green

# ── 6. Create distribution ZIP ──────────────────────────────────────
Write-Host "`n[5/5] Creating distribution ZIP..." -ForegroundColor Green
$version = (Get-Content (Join-Path $ROOT "VERSION")).Trim()
$zipName = "Rastro_v${version}_Windows.zip"
$zipPath = Join-Path $ROOT "dist" $zipName
if (Test-Path $zipPath) { Remove-Item $zipPath }

Add-Type -Assembly "System.IO.Compression.FileSystem"
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    (Join-Path $ROOT "dist" "Rastro"),
    $zipPath,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false
)

Write-Host "`n=== BUILD COMPLETE ===" -ForegroundColor Cyan
Write-Host "  EXE: $exe" -ForegroundColor White
Write-Host "  ZIP: $zipPath" -ForegroundColor White
Write-Host "  Size: $('{0:N1}' -f ((Get-Item $zipPath).Length / 1MB)) MB" -ForegroundColor White
