# -*- mode: python ; coding: utf-8 -*-
"""
Upbit Pro Algo-Trader v3.0 PyInstaller Spec File
빌드: pyinstaller upbit_trader.spec --clean
결과: dist/UpbitTrader/UpbitTrader.exe
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# pandas 전체 서브모듈 수집
pandas_imports = collect_submodules('pandas')
numpy_imports = collect_submodules('numpy')

# Hidden Imports
hiddenimports = [
    # pyupbit 및 의존성
    'pyupbit',
    'requests',
    'urllib3',
    'certifi',
    'charset_normalizer',
    'idna',
    'websocket',
    'websocket._abnf',
    'websocket._core',
    'websocket._exceptions',
    'jwt',
    
    # PyQt6
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
    'PyQt6.sip',
    
    # v3.0 선택 모듈
    'telegram',
    'telegram.ext',
    'cryptography',
    'cryptography.fernet',
    'matplotlib',
    'matplotlib.backends.backend_qtagg',
    'matplotlib.figure',
    
] + pandas_imports + numpy_imports

# 데이터 파일
datas = [
    ('telegram_notifier.py', '.'),
    ('crypto_utils.py', '.'),
    ('backtest_engine.py', '.'),
    ('strategies.py', '.'),
]

block_cipher = None

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
        # 확실히 불필요한 것만 제외
        'tkinter', '_tkinter',
        'unittest', 'pytest', '_pytest',
        'IPython', 'jupyter', 'notebook',
        'sphinx', 'docutils',
        
        # 불필요 PyQt6 모듈
        'PyQt6.QtBluetooth', 'PyQt6.QtDBus',
        'PyQt6.QtMultimedia', 'PyQt6.QtMultimediaWidgets',
        'PyQt6.QtNfc', 'PyQt6.QtOpenGL',
        'PyQt6.QtPositioning', 'PyQt6.QtQml',
        'PyQt6.QtQuick', 'PyQt6.QtQuickWidgets',
        'PyQt6.QtRemoteObjects', 'PyQt6.QtSensors',
        'PyQt6.QtSerialPort', 'PyQt6.QtSql',
        'PyQt6.QtWebChannel', 'PyQt6.QtWebEngine',
        'PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebSockets',
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
    upx=False,  # UPX 비활성화 (호환성)
    console=True,  # 디버깅용
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
    upx=False,
    upx_exclude=[],
    name='UpbitTrader',
)

# ============================================================
# 빌드: pyinstaller upbit_trader.spec --clean
# 결과: dist/UpbitTrader/UpbitTrader.exe
#
# 문제 해결 후 console=False 로 변경
# ============================================================
