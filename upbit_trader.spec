# -*- mode: python ; coding: utf-8 -*-
"""
Upbit Pro Algo-Trader v2.0 PyInstaller Spec File
업비트 자동매매 프로그램 빌드 설정

빌드 명령: pyinstaller upbit_trader.spec
"""

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# 히든 임포트 (PyInstaller가 자동 감지하지 못하는 모듈)
hiddenimports = [
    'pyupbit',
    'requests',
    'websocket',
    'pandas',
    'numpy',
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
        'matplotlib',
        'scipy',
        'tkinter',
        'unittest',
        'test',
        'tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 중복 바이너리 제거
a.binaries = list(set(a.binaries))

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

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
    icon=None,  # 아이콘 파일이 있으면 경로 지정: icon='icon.ico'
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

# =============================================================================
# 빌드 정보
# =============================================================================
# 
# 빌드 방법:
#   1. PyInstaller 설치: pip install pyinstaller
#   2. 빌드 실행: pyinstaller upbit_trader.spec
#
# 빌드 결과:
#   - dist/UpbitTrader/ 폴더에 실행 파일 생성
#   - UpbitTrader.exe 실행
#
# 옵션 설명:
#   - console=False: GUI 프로그램용 (콘솔 창 숨김)
#   - upx=True: 실행 파일 압축 (크기 감소)
#   - onedir 모드: 폴더 형태로 배포 (의존성 포함)
#
# 디버깅:
#   - console=True로 변경하면 오류 메시지 확인 가능
#   - 빌드 오류 시 --debug=all 옵션 추가
#
# =============================================================================
