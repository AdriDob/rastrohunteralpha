# ORION — Windows Uninstaller Script
# Run from the installed directory.
#
# Usage:
#   powershell -ExecutionPolicy Bypass uninstall_windows.ps1

$ErrorActionPreference = "Stop"

$DEST = Join-Path $env:LOCALAPPDATA "ORION"
$SHORTCUT_NAME = "ORION.lnk"
$UNINSTALL_KEY = "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\ORION"

Write-Host "=== ORION Uninstaller ===" -ForegroundColor Cyan

# ── Remove program files ────────────────────────────────────────────
if (Test-Path $DEST) {
    Remove-Item $DEST -Recurse -Force
    Write-Host "  ✓ Removed $DEST" -ForegroundColor Green
} else {
    Write-Host "  - Not found: $DEST" -ForegroundColor Yellow
}

# ── Remove shortcuts ───────────────────────────────────────────────
$paths = @(
    (Join-Path ([Environment]::GetFolderPath("CommonStartMenu")) "Programs" $SHORTCUT_NAME),
    (Join-Path ([Environment]::GetFolderPath("CommonDesktopDirectory")) $SHORTCUT_NAME),
    (Join-Path ([Environment]::GetFolderPath("CommonStartup")) $SHORTCUT_NAME),
    (Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs" $SHORTCUT_NAME),
    (Join-Path ([Environment]::GetFolderPath("Desktop")) $SHORTCUT_NAME),
    (Join-Path ([Environment]::GetFolderPath("Startup")) $SHORTCUT_NAME)
)

foreach ($p in $paths) {
    if (Test-Path $p) {
        Remove-Item $p -Force
        Write-Host "  ✓ Removed shortcut: $p" -ForegroundColor Green
    }
}

# ── Remove Add/Remove Programs entry ───────────────────────────────
if (Test-Path $UNINSTALL_KEY) {
    Remove-Item $UNINSTALL_KEY -Recurse -Force
    Write-Host "  ✓ Removed Add/Remove Programs entry" -ForegroundColor Green
}

# ── Optional: user data ────────────────────────────────────────────
$userData = Join-Path $env:USERPROFILE ".orion"
if (Test-Path $userData) {
    $choice = Read-Host "Remove user data (config, sessions, license)? (y/N)"
    if ($choice -eq "y" -or $choice -eq "Y") {
        Remove-Item $userData -Recurse -Force
        Write-Host "  ✓ Removed user data" -ForegroundColor Green
    }
}

Write-Host "=== ORION uninstalled ===" -ForegroundColor Cyan
