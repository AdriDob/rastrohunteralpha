#Requires -Version 5.1
<#
.SYNOPSIS
    Build Rastro v1.5.0 Windows binary from WSL source path.
.DESCRIPTION
    Runs PyInstaller from the WSL repo path to produce a Windows .exe.
    Skips frontend build (already exists from Linux build).
#>

$ErrorActionPreference = "Stop"

# Navigate to the repo via WSL UNC path
$ROOT = "\\wsl.localhost\Ubuntu\home\adrie\projects\Rastro"
Set-Location $ROOT
Write-Host "=== Building Rastro Windows binary (v1.5) ===" -ForegroundColor Cyan
Write-Host "  Root: $ROOT" -ForegroundColor White
Write-Host "  Version: $(Get-Content VERSION)" -ForegroundColor White

# ── 1. Verify prerequisites ──────────────────────────────────────
Write-Host "`n[1/5] Verifying prerequisites..." -ForegroundColor Green
$missing = @()
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { $missing += "Python" }
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) { $missing += "PyInstaller" }
if (-not (Test-Path "frontend/dist/index.html")) { $missing += "Frontend dist (run build_frontend.sh first)" }
if ($missing.Count -gt 0) {
    Write-Host "ERROR: Missing: $($missing -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "  All prerequisites met" -ForegroundColor Green

# ── 2. Install Python deps ───────────────────────────────────────
Write-Host "`n[2/5] Installing Python dependencies..." -ForegroundColor Green
pip install -q -r requirements.txt 2>&1 | Out-Null
Write-Host "  Dependencies installed" -ForegroundColor Green

# ── 3. PyInstaller build ─────────────────────────────────────────
Write-Host "`n[3/5] Running PyInstaller..." -ForegroundColor Green
pyinstaller Rastro.spec -y 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: PyInstaller failed" -ForegroundColor Red
    exit 1
}

# ── 4. Verify binary ─────────────────────────────────────────────
Write-Host "`n[4/5] Verifying output..." -ForegroundColor Green
$exe = Join-Path $ROOT "dist" "Rastro" "Rastro.exe"
if (-not (Test-Path $exe)) {
    Write-Host "ERROR: $exe not found" -ForegroundColor Red
    exit 1
}
$size = (Get-Item $exe).Length / 1MB
$sha = (Get-FileHash -Path $exe -Algorithm SHA256).Hash
Write-Host "  Binary: $exe" -ForegroundColor White
Write-Host "  Size: $('{0:N1}' -f $size) MB" -ForegroundColor White
Write-Host "  SHA256: $sha" -ForegroundColor White

# ── 5. Create dist ZIP ───────────────────────────────────────────
Write-Host "`n[5/5] Creating distribution ZIP..." -ForegroundColor Green
$version = (Get-Content "VERSION").Trim()
$zipName = "Rastro_v${version}_Windows.zip"
$zipPath = Join-Path $ROOT "dist" $zipName
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

Add-Type -Assembly "System.IO.Compression.FileSystem"
$distDir = Join-Path $ROOT "dist" "Rastro"
[System.IO.Compression.ZipFile]::CreateFromDirectory($distDir, $zipPath, [System.IO.Compression.CompressionLevel]::Optimal, $false)

$zipSize = (Get-Item $zipPath).Length / 1MB
Write-Host "  ZIP: $zipPath" -ForegroundColor White
Write-Host "  Size: $('{0:N1}' -f $zipSize) MB" -ForegroundColor White

# ── Done ─────────────────────────────────────────────────────────
Write-Host "`n=== BUILD COMPLETE ===" -ForegroundColor Cyan
Write-Host "  EXE: $exe ($('{0:N1}' -f $size) MB)" -ForegroundColor White
Write-Host "  SHA256: $sha" -ForegroundColor White
Write-Host "  ZIP: $zipName ($('{0:N1}' -f $zipSize) MB)" -ForegroundColor White
