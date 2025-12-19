# -*- mode: python ; coding: utf-8 -*-
"""
Upbit Pro Algo-Trader PyInstaller Spec File
업비트 자동매매 프로그램 빌드 설정
"""

import sys
from pathlib import Path

block_cipher = None

# 프로젝트 경로
project_path = Path(SPECPATH)

a = Analysis(
    ['upbit_trader.py'],
    pathex=[str(project_path)],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pyupbit',
        'pandas',
        'numpy',
        'requests',
        'websockets',
        'jwt',
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'PIL',
        'cv2',
        'tensorflow',
        'torch',
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
    [],
    exclude_binaries=True,
    name='UpbitTrader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI 프로그램이므로 콘솔 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 아이콘 파일이 있으면 경로 지정: 'icon.ico'
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
