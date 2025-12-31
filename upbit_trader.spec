# -*- mode: python ; coding: utf-8 -*-
"""
Upbit Pro Algo-Trader v3.0 PyInstaller Spec File
빌드: pyinstaller upbit_trader.spec
결과: dist/UpbitTrader/UpbitTrader.exe
"""

from PyInstaller.utils.hooks import collect_submodules

# 필수 Hidden Imports
hiddenimports = [
    # pyupbit
    'pyupbit',
    'requests',
    'websocket',
    'jwt',
    
    # pandas
    'pandas',
    'pandas._libs.tslibs.timedeltas',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.np_datetime',
    'pandas.core.arrays.masked',
    
    # numpy
    'numpy',
    'numpy.core._methods',
    'numpy.lib.format',
    
    # PyQt6
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
    'PyQt6.sip',
    
    # v3.0 모듈 (선택적)
    'telegram',
    'telegram.ext',
    'cryptography',
    'cryptography.fernet',
    'cryptography.hazmat.primitives',
    'cryptography.hazmat.primitives.kdf.pbkdf2',
    'matplotlib',
    'matplotlib.backends.backend_qtagg',
    'matplotlib.figure',
    'matplotlib.pyplot',
]

# v3.0 데이터 파일
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
        # GUI (tkinter 불필요)
        'tkinter', '_tkinter', 'Tkinter',
        
        # 과학 라이브러리
        'scipy', 'sklearn', 'scikit-learn',
        'PIL', 'Pillow', 'cv2', 'opencv',
        
        # 개발/문서
        'IPython', 'jupyter', 'notebook', 'ipykernel',
        'sphinx', 'docutils',
        
        # 테스트
        'unittest', 'test', 'tests', 'pytest', '_pytest',
        
        # 불필요 PyQt6 모듈
        'PyQt6.QtBluetooth', 'PyQt6.QtDBus', 'PyQt6.QtDesigner',
        'PyQt6.QtHelp', 'PyQt6.QtMultimedia', 'PyQt6.QtMultimediaWidgets',
        'PyQt6.QtNetwork', 'PyQt6.QtNfc', 'PyQt6.QtOpenGL',
        'PyQt6.QtPositioning', 'PyQt6.QtPrintSupport', 'PyQt6.QtQml',
        'PyQt6.QtQuick', 'PyQt6.QtQuickWidgets', 'PyQt6.QtRemoteObjects',
        'PyQt6.QtSensors', 'PyQt6.QtSerialPort', 'PyQt6.QtSql',
        'PyQt6.QtSvg', 'PyQt6.QtSvgWidgets', 'PyQt6.QtTest',
        'PyQt6.QtWebChannel', 'PyQt6.QtWebEngine', 'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebSockets', 'PyQt6.QtXml',
        'PyQt6.Qt3DAnimation', 'PyQt6.Qt3DCore', 'PyQt6.Qt3DExtras',
        'PyQt6.Qt3DInput', 'PyQt6.Qt3DLogic', 'PyQt6.Qt3DRender',
        
        # pandas 불필요
        'pandas.tests', 'pandas.plotting',
        
        # 기타
        'setuptools', 'pkg_resources', 'distutils',
        'email', 'html', 'http.server', 'xmlrpc',
        'lib2to3', 'pydoc_data',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 중복 제거
a.binaries = list(set(a.binaries))

# 불필요 DLL 제거
a.binaries = [b for b in a.binaries if not any(x in b[0].lower() for x in [
    'qt6webengine', 'qt6quick', 'qt6qml', 'qt6pdf',
    'qt6multimedia', 'qt6network', 'qt6positioning',
    'd3dcompiler', 'opengl32sw', 'libglesv2',
    'mkl_', 'tbb12',
])]

# 불필요 데이터 제거
a.datas = [d for d in a.datas if not any(x in d[0].lower() for x in [
    'translations', 'qtwebengine', 'locales',
])]

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

# ============================================================
# 빌드 방법:
#   pyinstaller upbit_trader.spec
#
# 경량화 빌드:
#   pyinstaller upbit_trader.spec --clean
#
# v3.0 포함 모듈:
#   - telegram_notifier.py (텔레그램)
#   - crypto_utils.py (암호화)
#   - backtest_engine.py (백테스팅)
#   - strategies.py (다중 전략)
#
# 결과: dist/UpbitTrader/UpbitTrader.exe
# ============================================================
