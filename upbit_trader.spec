# -*- mode: python ; coding: utf-8 -*-
"""
Upbit Pro Algo-Trader v2.7 PyInstaller Spec File (Onefile 버전)
빌드 명령: pyinstaller upbit_trader.spec --clean
결과: dist/UpbitTrader.exe

변경사항:
- Onefile 빌드 설정 (단일 실행 파일)
- Strip 비활성화 (Windows 빌드 오류 해결)
- 확장 모듈 포함
"""

from PyInstaller.utils.hooks import collect_submodules
import sys
import os

# 필수 의존성
hiddenimports = [
    'pyupbit', 'requests', 'websocket', 'jwt',
    'pandas', 'numpy', 
    'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui', 'PyQt6.sip',
    'csv', 'json', 'logging',
    # v2.7: 빌드 오류 해결 (jaraco 모듈)
    'jaraco', 'jaraco.text', 'jaraco.classes', 'jaraco.context', 'jaraco.functools',
    'pkg_resources.extern'
]

block_cipher = None

# 확장 모듈 파일 (소스와 같은 위치에 있다고 가정)
datas = [
    ('upbit_analytics.py', '.'),
    ('upbit_indicators.py', '.'),
    ('upbit_backtester.py', '.'),
    ('upbit_notifiers.py', '.'),
    # 설정 파일은 없으면 프로그램이 생성함
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
        'ipython', 'unittest', 'test', 'distutils', 'setuptools'
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

# Onefile 빌드는 EXE에 모든 것을 포함 (COLLECT 제거)
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
    strip=False,          # 오류 해결: strip 비활성화
    upx=True,             # UPX 압축 (가능한 경우)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,        # GUI 프로그램이므로 콘솔 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,            # 아이콘 파일이 있다면 'icon.ico' 등 지정
)
