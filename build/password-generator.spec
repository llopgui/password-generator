# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec para Password Generator

from pathlib import Path

block_cipher = None

# PyInstaller ejecuta el spec con `exec`, por eso `__file__` no existe aquí.
# `SPECPATH` apunta al directorio donde está este .spec.
SPEC_DIR = Path(SPECPATH).resolve()
ROOT_DIR = SPEC_DIR.parent
ICON_CANDIDATES = (
    ROOT_DIR / "assets" / "icon.ico",
    ROOT_DIR / "assets" / "app.ico",
)
ICON_PATH = next((str(path) for path in ICON_CANDIDATES if path.exists()), None)

a = Analysis(
    ["../generador.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("../dict", "dict"),
        ("../assets", "assets"),
        ("../config.example.json", "."),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="password-generator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_PATH,
)
