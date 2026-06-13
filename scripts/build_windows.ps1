# Rastro — Build Script Windows 11
# Ejecutar desde PowerShell como administrador

$WINPY = "C:\Users\adrie\AppData\Local\Programs\Python\Python312\python.exe"
$PROJECT = "\\wsl$\Ubuntu\home\adrie\projects\Rastro"
$DIST = "C:\Users\adrie\Rastro-Build\dist"
$BUILD = "C:\Users\adrie\Rastro-Build\build"

Write-Host "=== Rastro Build Pipeline ===" -ForegroundColor Cyan

# PyInstaller
Write-Host "Compilando exe..." -ForegroundColor Yellow
& $WINPY -m PyInstaller "$PROJECT\Rastro.spec" --clean -y `
  --distpath $DIST `
  --workpath $BUILD

# Copiar a Desktop
Write-Host "Copiando a Desktop..." -ForegroundColor Yellow
Copy-Item "$DIST\Rastro" "$env:USERPROFILE\Desktop\Rastro" -Recurse -Force

# Validar
Write-Host "Validando..." -ForegroundColor Yellow
$exe = "$env:USERPROFILE\Desktop\Rastro\Rastro.exe"
if (Test-Path $exe) {
    Write-Host "✓ Rastro.exe generado correctamente" -ForegroundColor Green
    Write-Host "  Tamaño: $((Get-Item $exe).Length / 1MB) MB"
} else {
    Write-Host "✗ Build falló" -ForegroundColor Red
}
