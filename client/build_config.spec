"""
PyInstaller Spec File for VPN Client
Optimized for GUI mode with embedded resources and code optimization
"""

import os
from pathlib import Path

# Build configuration
PROJECT_ROOT = Path(__file__).parent
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"

block_cipher = None

# Hidden imports (required by asyncio, PySide6, etc.)
hiddenimports = [
    'asyncio',
    'logging',
    'logging.handlers',
    'ssl',
    'socket',
    'struct',
    'hashlib',
    'hmac',
    'binascii',
    'base64',
    'json',
    'datetime',
    'time',
    'threading',
    'queue',
    'collections',
    'itertools',
    'functools',
    'weakref',
    'abc',
    'enum',
    'dataclasses',
    'pathlib',
    'tempfile',
    'shutil',
    'subprocess',
    're',
    'textwrap',
    'io',
    'sys',
    'os',
    'platform',
    # Cryptography
    'Cryptodome',
    'Cryptodome.Cipher',
    'Cryptodome.Cipher.ChaCha20_Poly1305',
    'Cryptodome.Protocol',
    'Cryptodome.Protocol.KDF',
    'Cryptodome.Random',
    'Cryptodome.Hash',
    'Cryptodome.Hash.SHA256',
    'Cryptodome.Hash.HMAC',
    # msgpack
    'msgpack',
    # YAML
    'yaml',
    # PySide6
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
]

# Binaries (DLLs, etc.)
binaries = []

# Data files
datas = [
    # GUI styles
    (str(PROJECT_ROOT / "client" / "gui" / "styles"), "client/gui/styles"),
    # Configuration file
    (str(PROJECT_ROOT / "client" / "client_config.yaml"), "client"),
]

# Executable analysis
a = Analysis(
    [str(PROJECT_ROOT / "client" / "gui_main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[
        'tkinter',
        'unittest',
        'doctest',
        'pydoc',
        'sqlite3',  # Not needed
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Optimize: Remove unnecessary modules
a.binaries = [x for x in a.binaries if 'msvc' not in x[0].lower() and 'api-ms' not in x[0].lower()]

# Build PYZ (archive)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Build EXE
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="VPN_Client",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disable UPX (causes false positives in antivirus)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI mode (no console window)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Can be set to icon file path
)

# Collect DLLs
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="VPN_Client",
)
