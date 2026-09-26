"""Central theme handling for the Upbit desktop UI.

Mirrors the srtgo ``ktrain.gui.theme`` pattern within the PyQt6 binding:

- ``setup_app_theme(app)`` is called once from ``main()``; it applies the
  OS-driven theme (``Theme.AUTO`` equivalent) and installs a watcher.
- ``sync_system_theme()`` re-reads the OS theme via ``darkdetect``
  (falls back to the current stylesheet when unavailable) and reapplies
  the single token-based global stylesheet.
- ``configure_main_window(window)`` sizes the window from the available
  screen geometry (no fixed 1200x900 assumption) so 125%/150% DPI and
  sub-1080p screens keep working.

Only this module (plus ``design_tokens``) owns hex colors and global QSS.
Pages must not call ``setStyleSheet`` with inline color strings.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QGuiApplication

from upbit_autotrader.ui import design_tokens as tokens

_DEFAULT_WINDOW_WIDTH = 1200
_DEFAULT_WINDOW_HEIGHT = 900
_MIN_WINDOW_WIDTH = 960
_MIN_WINDOW_HEIGHT = 680
_SCREEN_MARGIN = 40

_POLLED = False


def is_dark_mode() -> bool:
    """Best-effort OS dark-mode detection (darkdetect, else light)."""
    try:
        import darkdetect

        return darkdetect.theme() == "Dark"
    except Exception:
        return False


def preferred_window_size(avail_width: int, avail_height: int) -> tuple:
    """Default window size clamped to the available screen geometry."""
    width = min(_DEFAULT_WINDOW_WIDTH, max(_MIN_WINDOW_WIDTH, avail_width - _SCREEN_MARGIN))
    height = min(_DEFAULT_WINDOW_HEIGHT, max(_MIN_WINDOW_HEIGHT, avail_height - _SCREEN_MARGIN))
    return width, height


def build_stylesheet(dark: bool) -> str:
    """Single global stylesheet generated from design tokens."""
    c = tokens.palette(dark)
    return f"""
QWidget {{
    background-color: {c['background']};
    color: {c['text_primary']};
    font-family: {tokens.FONT_FAMILY};
    font-size: {tokens.FONT_BODY}px;
}}
QGroupBox {{
    background-color: {c['surface']};
    border: 1px solid {c['border']};
    border-radius: {tokens.CARD_RADIUS}px;
    margin-top: {tokens.SPACE_XS}px;
    padding-top: {tokens.SPACE_XS}px;
    font-size: {tokens.FONT_SECTION_TITLE}px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: {tokens.SPACE_XS}px;
    padding: 0 {tokens.SPACE_XXS}px;
    color: {c['text_secondary']};
}}
QLineEdit, QTextEdit, QListWidget, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {c['surface_alt']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    padding: 6px;
    color: {c['text_primary']};
    selection-background-color: {c['primary']};
}}
QPushButton {{
    background-color: {c['surface_alt']};
    border: 1px solid {c['border']};
    border-radius: 6px;
    padding: 6px {tokens.SPACE_SM}px;
    color: {c['text_primary']};
    min-height: {tokens.CONTROL_HEIGHT_SM - 8}px;
}}
QPushButton:disabled {{
    color: {c['text_secondary']};
}}
QPushButton:hover:!disabled {{
    border-color: {c['primary']};
}}
QPushButton[primary="true"] {{
    background-color: {c['primary']};
    border: none;
    color: #ffffff;
    font-weight: 600;
}}
QPushButton[destructive="true"] {{
    background-color: {c['error']};
    border: none;
    color: #ffffff;
    font-weight: 600;
}}
QPushButton[tradeBuy="true"] {{
    background-color: {tokens.TRADE_BUY};
    border: none;
    color: #ffffff;
    font-weight: 600;
}}
QPushButton[tradeBuy="true"]:hover:!disabled {{
    background-color: {tokens.TRADE_BUY_HOVER};
    border: none;
}}
QPushButton[tradeSell="true"] {{
    background-color: {tokens.TRADE_SELL};
    border: none;
    color: #ffffff;
    font-weight: 600;
}}
QPushButton[tradeSell="true"]:hover:!disabled {{
    background-color: {tokens.TRADE_SELL_HOVER};
    border: none;
}}
QTabWidget::pane {{
    border: 1px solid {c['border']};
    border-radius: {tokens.CARD_RADIUS}px;
    background-color: {c['surface']};
}}
QTabBar::tab {{
    padding: {tokens.SPACE_XS}px {tokens.SPACE_MD}px;
    margin-right: {tokens.SPACE_XXS}px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: {c['text_secondary']};
}}
QTabBar::tab:selected {{
    color: {c['text_primary']};
    background-color: {c['surface']};
    border: 1px solid {c['border']};
    border-bottom: none;
}}
QTableWidget {{
    background-color: {c['surface']};
    color: {c['text_primary']};
    gridline-color: {c['border']};
    alternate-background-color: {c['surface_alt']};
}}
QHeaderView::section {{
    background-color: {c['surface_alt']};
    color: {c['text_secondary']};
    border: none;
    padding: {tokens.SPACE_XS}px;
}}
QStatusBar {{
    background-color: {c['surface']};
    color: {c['text_secondary']};
    font-size: {tokens.FONT_SECONDARY}px;
}}
QToolTip {{
    background-color: {c['surface']};
    color: {c['text_primary']};
    border: 1px solid {c['border']};
}}
"""


def apply_theme(window: Any, dark: bool | None = None) -> bool:
    """Apply the token stylesheet to a top-level window. Returns dark flag."""
    use_dark = is_dark_mode() if dark is None else bool(dark)
    try:
        window.setStyleSheet(build_stylesheet(use_dark))
    except Exception:
        return use_dark
    return use_dark


def sync_system_theme() -> None:
    """Re-apply the OS theme to all top-level widgets (theme watcher slot)."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return
    use_dark = is_dark_mode()
    sheet = build_stylesheet(use_dark)
    for widget in QApplication.topLevelWidgets():
        try:
            widget.setStyleSheet(sheet)
        except Exception:
            continue


def _install_theme_watcher(app: Any) -> None:
    global _POLLED
    hints = QGuiApplication.styleHints()
    if hints is not None and hasattr(hints, "colorSchemeChanged"):
        try:
            hints.colorSchemeChanged.connect(lambda _s: QTimer.singleShot(0, sync_system_theme))
        except Exception:
            pass
    if _POLLED:
        return
    _POLLED = True
    try:
        timer = QTimer(app)
        timer.timeout.connect(sync_system_theme)
        timer.start(3000)
    except Exception:
        pass


def setup_app_theme(app: Any) -> None:
    """Call once from ``main()`` right after creating the QApplication."""
    apply_theme(app, dark=is_dark_mode())
    _install_theme_watcher(app)


def configure_main_window(window: Any) -> None:
    """Responsive initial geometry from the available screen area."""
    try:
        screen = QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen is not None else None
        if avail is not None:
            width, height = preferred_window_size(avail.width(), avail.height())
        else:
            width, height = _DEFAULT_WINDOW_WIDTH, _DEFAULT_WINDOW_HEIGHT
        window.resize(width, height)
        window.setMinimumSize(
            min(_MIN_WINDOW_WIDTH, width),
            min(_MIN_WINDOW_HEIGHT, height),
        )
    except Exception:
        pass
