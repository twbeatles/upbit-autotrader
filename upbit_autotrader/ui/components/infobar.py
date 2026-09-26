"""Non-modal notification banner (InfoBar equivalent, rules section 15).

Success/warning/error/info feedback that does not steal focus or block the
trading workflow. Modal ``QMessageBox`` stays reserved for destructive or
must-decide situations (rules section 18).
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from upbit_autotrader.ui import design_tokens as tokens
from upbit_autotrader.ui.theme import is_dark_mode

KINDS = ("success", "info", "warning", "error")

_DEFAULT_DURATION_MS = 6000


class InfoBar(QWidget):
    """Dismissible banner; use ``notify()`` instead of instantiating directly."""

    def __init__(self, title: str, message: str = "", kind: str = "info", parent=None) -> None:
        super().__init__(parent)
        if kind not in KINDS:
            kind = "info"
        self._kind = kind
        color = tokens.status_color(kind, is_dark_mode())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(tokens.SPACE_SM, tokens.SPACE_XS, tokens.SPACE_XS, tokens.SPACE_XS)
        layout.setSpacing(tokens.SPACE_XS)

        self.setStyleSheet(
            f"InfoBar {{ border: 1px solid {color}; border-radius: 6px; }}"
        )

        text = QLabel(f"<b>{title}</b> {message}" if message else f"<b>{title}</b>")
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(text, 1)

        close_btn = QPushButton("닫기")
        close_btn.setFlat(True)
        close_btn.clicked.connect(self.close_bar)
        layout.addWidget(close_btn)

    def kind(self) -> str:
        return self._kind

    def close_bar(self) -> None:
        self.setParent(None)
        self.deleteLater()


def _host_layout(host: Any):
    """Top-level vertical layout hosting banners, created on demand."""
    existing = host.findChild(QWidget, "infoBarHost")
    if existing is not None and existing.layout() is not None:
        return existing.layout(), existing
    container = QWidget(host)
    container.setObjectName("infoBarHost")
    layout = QVBoxLayout(container)
    layout.setContentsMargins(tokens.SPACE_MD, tokens.SPACE_XS, tokens.SPACE_MD, 0)
    layout.setSpacing(tokens.SPACE_XS)
    central = None
    try:
        central = host.centralWidget()
    except Exception:
        central = None
    if central is not None and central.layout() is not None:
        central.layout().insertWidget(0, container)
    return layout, container


def notify(host: Any, title: str, message: str = "", kind: str = "info",
           duration_ms: int = _DEFAULT_DURATION_MS) -> InfoBar | None:
    """Show a non-modal banner on ``host`` (a QMainWindow-like widget)."""
    try:
        layout, _container = _host_layout(host)
    except Exception:
        return None
    bar = InfoBar(title, message, kind, parent=host)
    if layout is not None:
        layout.addWidget(bar)
    if duration_ms > 0:
        QTimer.singleShot(duration_ms, bar.close_bar)
    # keep at most 3 banners visible
    if layout is None:
        return bar
    items = []
    for i in range(layout.count()):
        item = layout.itemAt(i)
        items.append(item.widget() if item is not None else None)
    bars = [w for w in items if isinstance(w, InfoBar)]
    for extra in bars[:-3]:
        try:
            extra.close_bar()
        except Exception:
            pass
    return bar


def notify_or_fallback(host: Any, kind: str, title: str, message: str = "",
                       fallback=None):
    """Prefer the non-modal InfoBar; run ``fallback`` when unavailable.

    ``fallback`` keeps the legacy modal path (and stays patchable in the
    caller's module, since it is resolved there at call time).
    """
    method = getattr(host, "notify_" + str(kind), None)
    if callable(method):
        try:
            return method(title, message)
        except Exception:
            pass
    if callable(fallback):
        try:
            return fallback()
        except Exception:
            pass
    return None


# re-export for drop-in familiarity with qfluentwidgets-style call sites
success = lambda host, title, message="": notify(host, title, message, "success")
info = lambda host, title, message="": notify(host, title, message, "info")
warning = lambda host, title, message="": notify(host, title, message, "warning")
error = lambda host, title, message="": notify(host, title, message, "error")
