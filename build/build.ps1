# Genera el ejecutable password-generator.exe.
# Ejecutar desde la raíz del proyecto: .\build\build.ps1

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

Set-Location $projectRoot

Write-Host "Instalando/actualizando PyInstaller..."
python -m pip install --upgrade pyinstaller --quiet

Write-Host ""
Write-Host "Generando ejecutable con build/password-generator.spec..."
python -m PyInstaller --clean --noconfirm build\password-generator.spec

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Listo. El ejecutable está en: dist\password-generator.exe"
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "Error al generar el ejecutable."
    exit 1
}
