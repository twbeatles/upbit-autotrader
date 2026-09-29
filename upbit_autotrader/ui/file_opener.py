"""Cross-platform local file/folder opener.

``os.startfile`` exists on Windows only; report/backtest export and log-folder
actions must use :func:`open_local_path` so non-Windows platforms degrade to a
best-effort opener instead of raising ``AttributeError``.
"""

from __future__ import annotations

import os
import subprocess
import sys


def open_local_path(path: str) -> bool:
    """Open *path* with the OS default handler. Returns True if launched."""
    try:
        if hasattr(os, "startfile"):
            os.startfile(path)  # type: ignore[attr-defined]
            return True
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
            return True
        subprocess.Popen(["xdg-open", path])
        return True
    except Exception:
        return False
