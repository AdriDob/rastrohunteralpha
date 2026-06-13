#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Rastro Desktop - Full Build Pipeline
    Single entrypoint: frontend build -> PyInstaller -> Desktop copy -> ZIP -> NSIS
#>

param(
    [switch]$Quick,
    [string]$Step = "all"
)

$ErrorActionPreference = "Stop"

# --- Config -----------------------------------------------------------
$WSL_DISTRO      = "Ubuntu"
$PROJECT_WSL     = "/home/adrie/projects/Rastro"
$WIN_PYTHON      = "C:\Users\adrie\AppData\Local\Programs\Python\Python312\python.exe"
$WIN_BUILD       = "C:\Users\adrie\Rastro-Build"
$WIN_PROJECT     = "$WIN_BUILD\project"
$WIN_DIST        = "$WIN_BUILD\dist"
$DESKTOP         = "C:\Users\adrie\Desktop"
$VERSION         = "1.0.0-rc1"
$SYNC_TAR        = "_rastro_sync.tar"

$WSL_SYNC_DEST = "/mnt/c/Users/adrie/Rastro-Build/project"

# --- Helpers -----------------------------------------------------------

function exec_step($name, $scriptBlock) {
    Write-Host "`n=== $name ===" -ForegroundColor Cyan
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        & $scriptBlock
        $sw.Stop()
        Write-Host "  [OK] $name ($($sw.Elapsed.TotalSeconds.ToString('0.0'))s)" -ForegroundColor Green
    } catch {
        $sw.Stop()
        Write-Host "  [FAIL] $name after $($sw.Elapsed.TotalSeconds.ToString('0.0'))s" -ForegroundColor Red
        Write-Host "  $_" -ForegroundColor Red
        if ($PSItem.Exception.InnerException) {
            Write-Host "  $($PSItem.Exception.InnerException.Message)" -ForegroundColor Red
        }
        exit 1
    }
}

function wsl_cmd($cmd) {
    $result = & "wsl.exe" "-d" $WSL_DISTRO "-e" "bash" "-c" $cmd 2>&1
    $ec = $LASTEXITCODE
    if ($ec -ne 0) {
        $snippet = if ($cmd.Length -gt 100) { $cmd.Substring(0, 100) + "..." } else { $cmd }
        throw "WSL exit ${ec}: $snippet"
    }
    return $result
}

# --- Step selection ----------------------------------------------------

$steps = @()
if ($Step -eq "all") {
    $steps = @("frontend", "sync", "pyi", "deploy", "zip", "nsis")
    if ($Quick) {
        $steps = $steps | Where-Object { $_ -ne "nsis" }
    }
} else {
    $steps = @($Step)
}

# --- 1. Frontend -------------------------------------------------------

if ("frontend" -in $steps) {
    exec_step "Build frontend" {
        wsl_cmd "cd $PROJECT_WSL/frontend && npm run build"
    }
}

# --- 2. Sync source files to Windows -----------------------------------

if ("sync" -in $steps) {
    exec_step "Sync source files to Windows" {
        # Step 2a: create tar archive on Windows filesystem
        wsl_cmd "cd $PROJECT_WSL && tar cf $WSL_SYNC_DEST/$SYNC_TAR --exclude=__pycache__ --exclude=*.pyc api core database desktop scripts frontend/dist Rastro.spec main.py"
        # Step 2b: extract archive at destination, then remove it
        wsl_cmd "cd $WSL_SYNC_DEST && tar xf $SYNC_TAR && rm -f $SYNC_TAR"
    }
}

# --- 3. PyInstaller ----------------------------------------------------

if ("pyi" -in $steps) {
    exec_step "PyInstaller" {
        wsl_cmd "cd $WSL_SYNC_DEST && C:/Users/adrie/AppData/Local/Programs/Python/Python312/python.exe -m PyInstaller Rastro.spec --clean -y --distpath C:/Users/adrie/Rastro-Build/dist --workpath C:/Users/adrie/Rastro-Build/build"
    }
}

# --- 4. Deploy to Desktop ----------------------------------------------

if ("deploy" -in $steps) {
    exec_step "Copy to Desktop" {
        $src = "$WIN_DIST\Rastro"
        $dst = "$DESKTOP\Rastro"
        if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
        Copy-Item $src $dst -Recurse
        $count = (Get-ChildItem "$dst\_internal" -Recurse -File).Count
        Write-Host "  Files: $count" -ForegroundColor Gray
    }
}

# --- 5. Portable ZIP ---------------------------------------------------

if ("zip" -in $steps) {
    exec_step "Portable ZIP" {
        & $WIN_PYTHON "$WIN_PROJECT\scripts\package_portable.py" --source "$WIN_DIST\Rastro" --output "$WIN_DIST" --version $VERSION
    }
}

# --- 6. NSIS Installer -------------------------------------------------

if ("nsis" -in $steps) {
    $makensis = @(
        "C:\Program Files (x86)\NSIS\makensis.exe",
        "C:\Program Files\NSIS\makensis.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1

    if (-not $makensis) {
        Write-Host "  [SKIP] NSIS not installed" -ForegroundColor Yellow
    } else {
        exec_step "NSIS Installer" {
            $ec = (Start-Process -FilePath $makensis -ArgumentList "$WIN_PROJECT\scripts\installer.nsi" -Wait -NoNewWindow -PassThru).ExitCode
            if ($ec -ne 0) { throw "makensis exit $ec" }
        }
    }
}

# --- Summary -----------------------------------------------------------

Write-Host "`n=== BUILD COMPLETE ===" -ForegroundColor Green
Write-Host "  Desktop: $DESKTOP\Rastro\Rastro.exe" -ForegroundColor White
Write-Host "  ZIP:     $WIN_DIST\Rastro-Portable-$VERSION.zip" -ForegroundColor White
if (Test-Path "$WIN_DIST\Rastro-Setup-$VERSION.exe") {
    Write-Host "  NSIS:    $WIN_DIST\Rastro-Setup-$VERSION.exe" -ForegroundColor White
}
Write-Host "`nValidate: curl http://127.0.0.1:8000/api/health" -ForegroundColor Gray
