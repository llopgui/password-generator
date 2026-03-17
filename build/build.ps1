# Genera el ejecutable password-generator.exe
# Ejecutar desde la raíz del proyecto: .\build\build.ps1

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

Set-Location $projectRoot

Write-Host "Instalando PyInstaller si no está disponible..."
pip install pyinstaller --quiet

Write-Host ""
Write-Host "Generando ejecutable..."
pyinstaller --clean --noconfirm build\password-generator.spec

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Listo. El ejecutable está en: dist\password-generator.exe"
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "Error al generar el ejecutable."
    exit 1
}
