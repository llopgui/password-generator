# Build de ejecutable

Esta carpeta contiene los recursos para generar `password-generator.exe` con PyInstaller.

## Archivos

- `build.ps1`: script de build para Windows PowerShell.
- `password-generator.spec`: configuración de PyInstaller.

## Requisitos

- Python 3.13+
- `pip`

## Uso rápido

Desde la raíz del proyecto:

```powershell
.\build\build.ps1
```

También puedes ejecutar PyInstaller directamente:

```powershell
python -m PyInstaller --clean --noconfirm build\password-generator.spec
```

## Salida

El binario final se genera en:

- `dist/password-generator.exe`

## Notas

- El `spec` incluye `dict/`, `assets/` y `config.example.json`.
- El icono se toma de `assets/icon.ico` cuando está disponible.
