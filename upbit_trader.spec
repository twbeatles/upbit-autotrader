# -*- mode: python ; coding: utf-8 -*-
"""
Upbit Pro Algo-Trader v2.6 PyInstaller Spec File (경량화 버전)
빌드 명령: pyinstaller upbit_trader.spec
결과: dist/UpbitTrader/UpbitTrader.exe
"""

from PyInstaller.utils.hooks import collect_submodules

# 필수 의존성만 명시
hiddenimports = [
    # pyupbit 핵심
    'pyupbit',
    'requests',
    'websocket',
    'jwt',
    
    # pandas 핵심 (최소화)
    'pandas',
    'pandas._libs.tslibs.timedeltas',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.tslibs.np_datetime',
    'pandas.core.arrays.masked',
    
    # numpy 핵심
    'numpy',
    
    # PyQt6 핵심
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtWidgets',
    'PyQt6.QtGui',
    'PyQt6.sip',
]

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
        # GUI 불필요
        'tkinter', '_tkinter', 'Tkinter',
        
        # 무거운 과학 라이브러리
        'matplotlib', 'scipy', 'sklearn', 'scikit-learn',
        'PIL', 'Pillow', 'cv2', 'opencv',
        
        # 문서/노트북
        'IPython', 'jupyter', 'notebook', 'ipykernel',
        'sphinx', 'docutils',
        
        # 테스트 관련
        'unittest', 'test', 'tests', 'pytest', '_pytest',
        
        # 불필요한 PyQt 모듈
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
        
        # pandas 불필요 모듈
        'pandas.tests', 'pandas.plotting',
        
        # 기타
        'setuptools', 'pkg_resources', 'distutils',
        'email', 'html', 'http.server', 'xmlrpc',
        'multiprocessing.popen_spawn_win32',
        'lib2to3', 'pydoc_data',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 중복 바이너리 제거
a.binaries = list(set(a.binaries))

# 불필요한 DLL 제거 (경량화)
a.binaries = [b for b in a.binaries if not any(x in b[0].lower() for x in [
    'qt6webengine', 'qt6quick', 'qt6qml', 'qt6pdf',
    'qt6multimedia', 'qt6network', 'qt6positioning',
    'd3dcompiler', 'opengl32sw', 'libglesv2',
    'mkl_', 'tbb12',  # Intel MKL 라이브러리 제외
])]

# 불필요한 데이터 파일 제거
a.datas = [d for d in a.datas if not any(x in d[0].lower() for x in [
    'translations', 'qtwebengine', 'resources',
    'locales', 'icons',
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
    strip=True,           # 심볼 제거 (경량화)
    upx=True,             # UPX 압축
    console=False,        # 콘솔 창 숨김
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
    strip=True,           # 심볼 제거
    upx=True,             # UPX 압축
    upx_exclude=[],
    name='UpbitTrader',
)

# ============================================================
# 빌드 방법:
#   pyinstaller upbit_trader.spec
#
# 추가 경량화 옵션 (선택):
#   pyinstaller upbit_trader.spec --clean
#
# UPX 설치 후 더 작은 빌드:
#   1. https://github.com/upx/upx/releases 에서 UPX 다운로드
#   2. upx.exe를 PATH에 추가 또는 PyInstaller 폴더에 복사
#   3. 위 명령 실행
#
# 결과: dist/UpbitTrader/UpbitTrader.exe
# ============================================================
