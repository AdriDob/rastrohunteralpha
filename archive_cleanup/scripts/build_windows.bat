@echo off
setlocal enabledelayedexpansion

REM ===========================================================================
REM  Rastro Desktop RC1 — Windows Build Script
REM  Produces: dist/Rastro/Rastro.exe + dist/Rastro-Setup-1.0.0.exe
REM
REM  Requirements:
REM    - Python 3.13+
REM    - PyInstaller  (pip install pyinstaller)
REM    - NSIS 3.x    (https://nsis.sourceforge.io/Download)
REM
REM  Usage:
REM    scripts\build_windows.bat           Full build (PyInstaller + NSIS)
REM    scripts\build_windows.bat --pyi     PyInstaller only
REM    scripts\build_windows.bat --nsis    NSIS only (after PyInstaller)
REM    scripts\build_windows.bat --portable  Build portable ZIP only
REM    scripts\build_windows.bat --all     Full pipeline
REM ===========================================================================

set VERSION=1.0.0
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set DIST_DIR=%PROJECT_DIR%\dist
set OUTPUT_DIR=%DIST_DIR%\Rastro
set NSIS_SCRIPT=%PROJECT_DIR%\scripts\installer.nsi
set ICON_PATH=%PROJECT_DIR%\desktop\build\icons\rastro.ico

:: Parse arguments
set BUILD_PYI=0
set BUILD_NSIS=0
set BUILD_PORTABLE=0

if "%1"=="" (
    set BUILD_PYI=1
    set BUILD_NSIS=1
    set BUILD_PORTABLE=1
) else if "%1"=="--pyi" (
    set BUILD_PYI=1
) else if "%1"=="--nsis" (
    set BUILD_NSIS=1
) else if "%1"=="--portable" (
    set BUILD_PORTABLE=1
) else if "%1"=="--all" (
    set BUILD_PYI=1
    set BUILD_NSIS=1
    set BUILD_PORTABLE=1
)

echo ===========================================================================
echo  Rastro Desktop RC1 — Windows Build v%VERSION%
echo ===========================================================================
echo.

:: Phase 1: PyInstaller
if %BUILD_PYI%==1 (
    echo [1/3] Building executable with PyInstaller...
    cd /d "%PROJECT_DIR%"
    pyinstaller Rastro.spec --clean -y
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] PyInstaller build failed
        exit /b 1
    )
    echo [OK] Executable: %OUTPUT_DIR%\Rastro.exe
    echo.
)

:: Phase 2: Portable ZIP
if %BUILD_PORTABLE%==1 (
    echo [2/3] Creating portable ZIP...
    powershell -Command "& {
        $src = '%OUTPUT_DIR%';
        $dst = '%DIST_DIR%\Rastro-Portable-%VERSION%.zip';
        if (Test-Path $dst) { Remove-Item $dst }
        Add-Type -Assembly 'System.IO.Compression.FileSystem';
        [System.IO.Compression.ZipFile]::CreateFromDirectory($src, $dst, 'Optimal', $false);
        Write-Host ('[OK] Portable: ' + $dst);
    }"
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] ZIP creation failed
    )
    echo.
)

:: Phase 3: NSIS Installer
if %BUILD_NSIS%==1 (
    echo [3/3] Building NSIS installer...
    if not exist "%NSIS_SCRIPT%" (
        echo [ERROR] NSIS script not found: %NSIS_SCRIPT%
        exit /b 1
    )
    "%PROGRAMFILES%\NSIS\makensis.exe" "%NSIS_SCRIPT%"
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] NSIS build failed
        exit /b 1
    )
    echo [OK] Installer: %DIST_DIR%\Rastro-Setup-%VERSION%.exe
    echo.
)

echo ===========================================================================
echo  Build complete.
echo.
if %BUILD_PYI%==1 (
    echo  Executable: dist\Rastro\Rastro.exe
)
if %BUILD_PORTABLE%==1 (
    echo  Portable:   dist\Rastro-Portable-%VERSION%.zip
)
if %BUILD_NSIS%==1 (
    echo  Installer:  dist\Rastro-Setup-%VERSION%.exe
)
echo ===========================================================================
