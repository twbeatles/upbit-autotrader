# -*- mode: python ; coding: utf-8 -*-
"""
Upbit Pro Algo-Trader PyInstaller spec (onefile, current modular build).

Build:
  pyinstaller --noconfirm --clean upbit_trader.spec
  # Repo-local fallback (artifacts ignored by .gitignore):
  # pyinstaller --noconfirm --clean --distpath upbit_dist --workpath upbit_build upbit_trader.spec
  # If this repo is on Google Drive (G:) and you see PermissionError writing .exe:
  # pyinstaller --noconfirm --clean --distpath C:\\temp\\upbit_dist --workpath C:\\temp\\upbit_build upbit_trader.spec

Output:
  dist/UpbitTrader.exe (default)
  build/                 (default workpath)
  upbit_dist/UpbitTrader.exe (repo-local fallback)
  upbit_build/           (repo-local fallback workpath)
"""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)

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
    "darkdetect",

    # PySide6 (explicit so modulegraph doesn't miss subpackages used indirectly)
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "PySide6.QtGui",
    "shiboken6",

    # setuptools/pkg_resources sometimes pulls these in indirectly
    "jaraco.text",
    "jaraco.classes",
    "jaraco.context",
    "jaraco.functools",
    "platformdirs",
]

# Refactored package modules
# Includes app bootstrap/runtime helpers, controllers/trading_parts/,
# controllers/ui_parts/, market_regime/, risk/, execution/,
# services/rate_limit.py, services/pyupbit_compat.py,
# strategies/meta_signal.py, and the type-support shim in controllers/_type_support.py.
hiddenimports += collect_submodules("upbit_autotrader")
hiddenimports += collect_submodules("legacy_wrappers")

# Fluent widgets (same-Qt-binding PySide6 edition, mirroring the reference
# frozen recipe): resource files plus every submodule except the unused
# multimedia/webengine paths.
hiddenimports += [
    name
    for name in collect_submodules("qfluentwidgets")
    if "multimedia" not in name
]
hiddenimports += [
    name
    for name in collect_submodules("qframelesswindow")
    if "webengine" not in name
]

_fluent_metadata = []
for _pkg in ("PySide6-Fluent-Widgets", "PySideSix-Frameless-Window", "qfluentwidgets"):
    try:
        _fluent_metadata += copy_metadata(_pkg)
    except Exception:
        pass

# NOTE:
# - Do not bundle local .py files as data; PyInstaller packages them as modules.
# - Runtime JSON/log files (settings/history/reconciliation/logs) remain external user data.
# - typings/ is for local pyright only and is intentionally not bundled.
datas = _fluent_metadata + collect_data_files("qfluentwidgets", include_py_files=False)

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
        "PySide6.QtWebEngine",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PyQt5",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "PySide2",
        "PyQt6",
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

# Python 3.15 abi3t: cryptography _rust.pyd links python3t.dll
# (<prefix>\abi3t-compat), which PyInstaller does not auto-collect.
# Without it the frozen exe dies with "DLL load failed while importing _rust".
_py3t_dll = os.path.join(sys.base_prefix, 'abi3t-compat', 'python3t.dll')
_py3t_dest = 'python3t.dll'
if os.path.isfile(_py3t_dll) and not any(
        (b[0] or '').lower() == _py3t_dest for b in a.binaries):
    a.binaries.append((_py3t_dest, _py3t_dll, 'BINARY'))

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
