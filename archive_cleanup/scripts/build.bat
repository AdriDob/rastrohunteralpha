@echo off
REM Rastro Desktop — Build Launcher
REM Invokes build.ps1 with bypass execution policy.
REM Usage: build.bat [--quick] [--step stepname]

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& '%~dpn0.ps1' %*"
if %ERRORLEVEL% neq 0 (
    echo.
    echo Build FAILED (exit code %ERRORLEVEL%^)
    pause
    exit /b %ERRORLEVEL%
)
