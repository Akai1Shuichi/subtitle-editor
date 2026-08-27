# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from pathlib import Path
from PyInstaller.building.build_main import Analysis, PYZ, EXE

block_cipher = None

# Thư mục gốc của project subtitle-editor
SPEC_DIR = Path(__file__).parent if '__file__' in globals() else Path.cwd()

datas = [
    (str(SPEC_DIR / 'data'), 'data'),
]

binaries_dir = SPEC_DIR / 'binaries'
if binaries_dir.is_dir():
    datas.append((str(binaries_dir), 'binaries'))

binaries = []

hiddenimports = [
    'pysubs2',
    'PIL',
]

icon_path = SPEC_DIR.parent / "SEditor" / "Assets" / "SEditor.ico"
icon_file = str(icon_path) if icon_path.is_file() else None

a = Analysis(
    [str(SPEC_DIR / 'run.py')],
    pathex=[str(SPEC_DIR)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'tests'],
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
    name='subtitle_editor',
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
    icon=icon_file,
)
