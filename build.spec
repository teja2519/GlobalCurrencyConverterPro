# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for Global Currency Converter Pro.
#
# Build with:   pyinstaller build.spec
#
# Notes:
#   * data/ and assets/ are bundled so the app has its CSV/JSON store
#     locations and the app icon available on first run.
#   * customtkinter ships its own theme JSON files that PyInstaller's
#     default hooks don't always pick up automatically, so they're added
#     explicitly via collect_data_files below.
#   * On Windows, icon='assets/icon.ico'; on macOS, PyInstaller will use
#     the same .ico (or swap in a .icns if you generate one) — both
#     platforms tolerate the cross-reference fine for a single-file spec.

import customtkinter
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
ctk_data = collect_data_files("customtkinter")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=ctk_data + [
        ("assets", "assets"),
    ],
    hiddenimports=[
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="GlobalCurrencyConverterPro",
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
    icon="assets/icon.ico",
)
