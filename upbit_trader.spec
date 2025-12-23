# -*- mode: python ; coding: utf-8 -*-
"""
Upbit Pro Algo-Trader v2.5 PyInstaller Spec File
빌드 명령: pyinstaller upbit_trader.spec
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [
    'pyupbit',
    'pandas',
    'pandas._libs.tslibs.timedeltas',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.np_datetime',
    'numpy',
    'requests',
    'websocket',
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
    'PyQt6.sip',
]

# pandas 서브모듈 수집
hiddenimports += collect_submodules('pandas')

block_cipher = None

a = Analysis(
    ['upbit_trader.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'tkinter',
        'unittest', 'test', 'tests',
        'PIL', 'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

a.binaries = list(set(a.binaries))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='UpbitTrader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='UpbitTrader',
)

# 빌드: pyinstaller upbit_trader.spec
# 결과: dist/UpbitTrader/UpbitTrader.exe
