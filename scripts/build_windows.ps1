# Rastro — Windows Build Script
# Run from PowerShell: .\scripts\build_windows.ps1

$ROOT = Split-Path -Parent $PSScriptRoot

Write-Host "=== Rastro — Windows Build ===" -ForegroundColor Cyan

# 1. Frontend
Write-Host "→ Building frontend..." -ForegroundColor Yellow
Push-Location "$ROOT\frontend"
npm install --silent
npm run build
Pop-Location

# 2. PyInstaller
Write-Host "→ Packaging desktop executable..." -ForegroundColor Yellow
pyinstaller "$ROOT\Rastro.spec" -y

Write-Host "✓ Windows build complete" -ForegroundColor Green
Write-Host "  Output: $ROOT\dist\Rastro\Rastro.exe"
if (Test-Path "$ROOT\dist\Rastro\Rastro.exe") {
    $size = (Get-Item "$ROOT\dist\Rastro\Rastro.exe").Length / 1MB
    Write-Host "  Size: $([math]::Round($size, 1)) MB"
}
