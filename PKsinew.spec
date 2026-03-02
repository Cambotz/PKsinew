# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import platform

# Detection logic for cross-platform builds
is_windows = os.name == 'nt'
is_arm = 'arm' in platform.machine().lower() or 'aarch64' in platform.machine().lower()
is_mac = sys.platform == 'darwin'

# UPX is helpful on Windows x86, but can break Mac/ARM binaries
use_upx = is_windows and not is_arm

block_cipher = None

icon = None
if is_mac:
    icon = 'assets/pksinew.icns'
elif is_windows:
    icon = 'assets/pksinew.ico'

a = Analysis(
    ['src/__main__.py'],
    pathex=[os.path.abspath('.')],
    binaries=[],
    datas=[
        ('src/cores', 'cores'),
        ('src/fonts', 'fonts'),
        ('src/parser', 'parser'),
        ('src/DBbuilder.py', '.'),
        ('src/wallgen.py', '.'),
        ('src/providers', 'providers')
    ],
    hiddenimports=[
        'requests', 
        'urllib3', 
        'charset_normalizer', 
        'idna', 
        'certifi',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFilter',
        'PIL.ImageFont'
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
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
    name='PKsinew',
    icon=icon,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=use_upx,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)