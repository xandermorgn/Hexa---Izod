# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for Izod Tester application.
# Build with:   pyinstaller izod.spec
#
# Produces a single-file, windowed executable:
#   dist\Izod.exe
#
# The SQLite database (izod_tests.db) is created automatically
# next to Izod.exe the first time the app is launched, and is
# re-created automatically if it is deleted.

block_cipher = None

a = Analysis(
    ['ui_main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Bundled read-only assets (landed in _MEIPASS at runtime)
        ('hexa_logo.ico',             '.'),
        ('hexaplast_logo_gray.svg',   '.'),
        ('hexaplast_logo_white.svg',  '.'),
    ],
    hiddenimports=[
        # PyQt6 modules that PyInstaller may miss
        'PyQt6.QtPrintSupport',
        'PyQt6.QtSvg',
        'PyQt6.QtSvgWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        # pyserial
        'serial',
        'serial.tools',
        'serial.tools.list_ports',
        'serial.tools.list_ports_windows',
        # stdlib used at runtime
        'sqlite3',
        'json',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim unused heavy packages
        'tkinter',
        'matplotlib',
        'numpy',
        'PIL',
        'cv2',
        'scipy',
        'pandas',
    ],
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
    name='Izod',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows application icon
    icon='hexa_logo.ico',
)
