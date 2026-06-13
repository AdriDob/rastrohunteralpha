# Rastro — Windows Installer Script
# Run as Administrator from the build output directory.
#
# Usage:
#   powershell -ExecutionPolicy Bypass installer\install_windows.ps1
#
# This script copies Rastro to LOCALAPPDATA and creates Start Menu shortcuts.

$ErrorActionPreference = "Stop"

$SOURCE = Join-Path $PSScriptRoot ".." "dist" "Rastro"
$DEST = Join-Path $env:LOCALAPPDATA "Rastro"
$EXE = Join-Path $DEST "Rastro.exe"
$SHORTCUT_NAME = "Rastro.lnk"

Write-Host "=== Rastro Windows Installer ===" -ForegroundColor Cyan

# ── Validate source ──────────────────────────────────────────────────
if (-not (Test-Path $SOURCE)) {
    Write-Host "✗ Source not found: $SOURCE" -ForegroundColor Red
    Write-Host "  Build first: scripts\build_windows.ps1"
    exit 1
}
if (-not (Test-Path (Join-Path $SOURCE "Rastro.exe"))) {
    Write-Host "✗ Rastro.exe not found in $SOURCE" -ForegroundColor Red
    exit 1
}

# ── Copy to LOCALAPPDATA ─────────────────────────────────────────────
Write-Host "→ Installing to $DEST ..." -ForegroundColor Yellow
if (Test-Path $DEST) {
    Remove-Item $DEST -Recurse -Force
}
New-Item -ItemType Directory -Path $DEST -Force | Out-Null
Copy-Item "$SOURCE\*" $DEST -Recurse -Force

# Also copy the uninstaller
$uninstallSource = Join-Path $PSScriptRoot "uninstall_windows.ps1"
if (Test-Path $uninstallSource) {
    Copy-Item $uninstallSource $DEST -Force
    Write-Host "  ✓ Uninstaller copied" -ForegroundColor Green
}

# ── Verify ───────────────────────────────────────────────────────────
if (-not (Test-Path $EXE)) {
    Write-Host "✗ Installation failed: $EXE not found" -ForegroundColor Red
    exit 1
}
$size = (Get-Item $EXE).Length / 1MB
Write-Host "  ✓ Rastro.exe ($([math]::Round($size, 1)) MB)" -ForegroundColor Green

# ── Create Start Menu shortcut ──────────────────────────────────────
$WScriptShell = New-Object -ComObject WScript.Shell
$StartMenu = [Environment]::GetFolderPath("CommonStartMenu")
$ShortcutPath = Join-Path $StartMenu "Programs" $SHORTCUT_NAME

$shortcut = $WScriptShell.CreateShortcut($ShortcutPath)
$shortcut.TargetPath = $EXE
$shortcut.WorkingDirectory = $DEST
$shortcut.Description = "Rastro Investigation OS"
$shortcut.Save()

Write-Host "  ✓ Start Menu shortcut created" -ForegroundColor Green

# ── Optional: Desktop shortcut ──────────────────────────────────────
$Desktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
$DesktopShortcut = Join-Path $Desktop $SHORTCUT_NAME
if (-not (Test-Path $DesktopShortcut)) {
    $shortcut2 = $WScriptShell.CreateShortcut($DesktopShortcut)
    $shortcut2.TargetPath = $EXE
    $shortcut2.WorkingDirectory = $DEST
    $shortcut2.Description = "Rastro Investigation OS"
    $shortcut2.Save()
    Write-Host "  ✓ Desktop shortcut created" -ForegroundColor Green
}

# ── Optional: Autostart ─────────────────────────────────────────────
$Startup = [Environment]::GetFolderPath("CommonStartup")
$StartupShortcut = Join-Path $Startup $SHORTCUT_NAME
$choice = Read-Host "Add Rastro to startup? (y/N)"
if ($choice -eq "y" -or $choice -eq "Y") {
    $shortcut3 = $WScriptShell.CreateShortcut($StartupShortcut)
    $shortcut3.TargetPath = $EXE
    $shortcut3.WorkingDirectory = $DEST
    $shortcut3.Description = "Rastro Investigation OS"
    $shortcut3.Save()
    Write-Host "  ✓ Autostart shortcut created" -ForegroundColor Green
}

# ── Add/Remove Programs entry ──────────────────────────────────────
$uninstallKey = "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Rastro"
$uninstallScript = Join-Path $DEST "uninstall_windows.ps1"

New-Item -Path $uninstallKey -Force | Out-Null
Set-ItemProperty -Path $uninstallKey -Name "DisplayName" -Value "Rastro Investigation OS"
Set-ItemProperty -Path $uninstallKey -Name "DisplayVersion" -Value "1.0.0"
Set-ItemProperty -Path $uninstallKey -Name "Publisher" -Value "Rastro"
Set-ItemProperty -Path $uninstallKey -Name "UninstallString" -Value "powershell -ExecutionPolicy Bypass `"$uninstallScript`""
Set-ItemProperty -Path $uninstallKey -Name "DisplayIcon" -Value "`"$EXE`""
Set-ItemProperty -Path $uninstallKey -Name "InstallLocation" -Value "`"$DEST`""

Write-Host "  ✓ Add/Remove Programs entry created" -ForegroundColor Green

Write-Host "=== Installation complete ===" -ForegroundColor Cyan
Write-Host "  Run: $EXE"
Write-Host "  Or search 'Rastro' in Start Menu"
