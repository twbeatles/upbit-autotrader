# -*- mode: python ; coding: utf-8 -*-
"""
Upbit Pro Algo-Trader v3.0 PyInstaller Spec File
빌드 명령: pyinstaller upbit_trader.spec --clean
결과: dist/UpbitTrader.exe
"""

import sys
import os

# 필수 의존성 (jaraco 모듈 명시적 포함)
hiddenimports = [
    'pyupbit', 'requests', 'websocket', 'jwt',
    'pandas', 'numpy', 
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui', 'PyQt6.sip',
    'csv', 'json', 'logging',
    'pkg_resources.extern',
    'jaraco', 'jaraco.text', 'jaraco.classes', 'jaraco.context', 'jaraco.functools', 'jaraco.collections',
    'platformdirs',
]

block_cipher = None

# v3.0: 모듈화된 파일들 + 확장 모듈
datas = [
    # v3.0 핵심 모듈
    ('upbit_config.py', '.'),
    ('upbit_strategy.py', '.'),
    ('upbit_dialogs.py', '.'),
    # v2.7 확장 모듈
    ('upbit_analytics.py', '.'),
    ('upbit_indicators.py', '.'),
    ('upbit_backtester.py', '.'),
    ('upbit_notifiers.py', '.'),
]

a = Analysis(
    ['upbit_trader.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'scipy', 'sklearn', 'PIL', 'cv2', 'notebook', 'jupyter',
        'PyQt6.QtWebEngine', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtQml', 'PyQt6.QtQuick', 'PyQt6.Qt3DCore', 'PyQt6.Qt3DRender',
        'ipython', 'unittest', 'test',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 다이어트: 불필요한 바이너리 제거
a.binaries = [x for x in a.binaries if not any(name in x[0].lower() for name in [
    'opengl32sw', 'd3dcompiler', 'libglesv2', 'qt6webengine', 'qt6quick', 'qt6qml'
])]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='UpbitTrader',
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
    icon=None,
)
