# -*- mode: python ; coding: utf-8 -*-
"""
Upbit Pro Algo-Trader v3.2.1 PyInstaller spec (onefile).

Build:
  pyinstaller --noconfirm --clean upbit_trader.spec
  # If this repo is on Google Drive (G:) and you see PermissionError writing .exe:
  # pyinstaller --noconfirm --clean --distpath C:\\temp\\upbit_dist --workpath C:\\temp\\upbit_build upbit_trader.spec

Output:
  dist/UpbitTrader.exe
"""

from pathlib import Path

block_cipher = None

project_root = Path(SPECPATH).resolve()

hiddenimports = [
    # Third-party
    "pyupbit",
    "requests",
    "websocket",
    "jwt",
    "pandas",
    "numpy",

    # PyQt6 (explicit so modulegraph doesn't miss subpackages used indirectly)
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtWidgets",
    "PyQt6.QtGui",
    "PyQt6.sip",

    # Local modules that can be imported dynamically/optionally
    "upbit_strategy",
    "upbit_dialogs",
    "upbit_dialog_fallbacks",
    "upbit_trader_ui_controller",
    "upbit_trader_settings_controller",
    "upbit_trader_history_controller",
    "upbit_trader_trading_controller",
    "upbit_trader_batch_controller",
    "upbit_price_thread",
    "upbit_security",
    "upbit_settings_store",
    "upbit_order_service",
    "upbit_paper_order_service",
    "upbit_holdings_service",
    "upbit_entry_filter",
    "upbit_strategy_engine",
    "upbit_strategy_catalog",
    "upbit_analytics",
    "upbit_backtester",

    # setuptools/pkg_resources sometimes pulls these in indirectly
    "jaraco.text",
    "jaraco.classes",
    "jaraco.context",
    "jaraco.functools",
    "platformdirs",
]

# NOTE: Do not bundle local .py files as data; PyInstaller packages them as modules.
datas = []

a = Analysis(
    ["upbit_trader.py"],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "scipy",
        "sklearn",
        "PIL",
        "cv2",
        "notebook",
        "jupyter",
        "PyQt6.QtWebEngine",
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtQml",
        "PyQt6.QtQuick",
        "PyQt6.Qt3DCore",
        "PyQt6.Qt3DRender",
        "PyQt5",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "PySide2",
        "PySide6",
        "qtpy",
        "ipython",
        "unittest",
        "test",
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
    name="UpbitTrader",
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
