"""Fluent-style navigation shell (PyQt6 port of the ktrain MSFluentWindow pattern).

Reference: ``ktrain.gui.main_window`` (srtgo) — ``MSFluentWindow`` with
``addSubInterface(page, icon, text, position)`` navigation, top-level pages
up top and auxiliary pages (settings/update) pinned to the bottom.

This project stays on PyQt6 with zero new dependencies
(``DESKTOP_UI_DESIGN_RULES.md`` section 1.1 forbids a binding switch and
mixed Fluent distributions), so the reference structure — sidebar rail,
top/bottom sections, stacked pages, ``addSubInterface``/``switchTo`` —
is re-implemented with native Qt widgets. All visuals come from the
central token stylesheet (``upbit_autotrader.ui.theme``); this module
owns no colors and calls ``setStyleSheet`` nowhere.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from upbit_autotrader.ui import design_tokens as tokens


class NavigationItemPosition:
    """Mirror of ``qfluentwidgets.NavigationItemPosition``."""

    TOP = 0
    BOTTOM = 1


RAIL_WIDTH = 200
RAIL_ICON_SIZE = 16


class FluentNavRail(QWidget):
    """Sidebar rail: top items, stretch, bottom items (single selection)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("navRail")
        self.setFixedWidth(RAIL_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._keys: list[str] = []
        self._buttons: dict[str, QPushButton] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(tokens.SPACE_MD, tokens.SPACE_MD, tokens.SPACE_MD, tokens.SPACE_MD)
        outer.setSpacing(tokens.SPACE_XS)

        self._top_box = QVBoxLayout()
        self._top_box.setSpacing(tokens.SPACE_XS)
        outer.addLayout(self._top_box)
        outer.addStretch(1)
        self._bottom_box = QVBoxLayout()
        self._bottom_box.setSpacing(tokens.SPACE_XS)
        outer.addLayout(self._bottom_box)

    def add_item(
        self,
        key: str,
        text: str,
        icon=None,
        position: int = NavigationItemPosition.TOP,
    ) -> QPushButton:
        """Append a checkable rail button; returns it for signal wiring."""
        button = QPushButton(text)
        button.setCheckable(True)
        button.setProperty("navItem", True)
        button.setProperty("navSelected", False)
        button.setMinimumHeight(tokens.CONTROL_HEIGHT_MD)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        if icon is not None:
            try:
                button.setIcon(icon)
                button.setIconSize(QSize(RAIL_ICON_SIZE, RAIL_ICON_SIZE))
            except Exception:
                pass
        self._group.addButton(button)
        self._keys.append(key)
        self._buttons[key] = button
        box = self._top_box if position == NavigationItemPosition.TOP else self._bottom_box
        box.addWidget(button)
        return button

    def set_selected(self, key: str) -> None:
        """Mark exactly one button selected (idempotent, safe to call anytime)."""
        for name, button in self._buttons.items():
            selected = name == key
            try:
                button.setChecked(selected)
                button.setProperty("navSelected", selected)
                nav_style = button.style()
                if nav_style is not None:
                    nav_style.unpolish(button)
                    nav_style.polish(button)
            except Exception:
                pass

    def top_keys(self) -> list[str]:
        """Keys in insertion order (the shell keeps the legacy page order)."""
        return list(self._keys)

    def button(self, key: str) -> QPushButton | None:
        """Accessor for tests/diagnostics."""
        return self._buttons.get(key)


class NavigationShell:
    """Owns a rail + page stack; mirrors ``MSFluentWindow`` navigation API."""

    def __init__(self, rail: FluentNavRail, stack: QStackedWidget) -> None:
        self.rail = rail
        self.stack = stack
        self._keys: list[str] = []
        self._pages: dict[str, QWidget] = {}

    def addSubInterface(
        self,
        page: QWidget,
        icon,
        text: str,
        position: int = NavigationItemPosition.TOP,
        key: str | None = None,
    ) -> str:
        """Register ``page`` under a rail button; returns the item key."""
        item_key = key or text
        self.stack.addWidget(page)
        button = self.rail.add_item(item_key, text, icon, position)
        button.clicked.connect(lambda _checked=False, k=item_key: self.switch_to(k))
        self._keys.append(item_key)
        self._pages[item_key] = page
        if len(self._keys) == 1:
            self.switch_to(item_key)
        return item_key

    def switch_to(self, key: str) -> None:
        """Show the page registered under ``key`` (unknown keys ignored)."""
        page = self._pages.get(key)
        if page is None:
            return
        try:
            self.stack.setCurrentWidget(page)
        except Exception:
            return
        self.rail.set_selected(key)

    def page(self, key: str) -> QWidget | None:
        """Accessor for tests/diagnostics."""
        return self._pages.get(key)

    def keys(self) -> list[str]:
        """Page keys in registration (legacy) order."""
        return list(self._keys)

    # Alias matching the reference ``MSFluentWindow.switchTo`` name.
    switchTo = switch_to


def create_shell() -> tuple[QWidget, NavigationShell]:
    """Build the rail + page-stack container and its controller.

    Returns ``(container, shell)``; callers register pages with
    ``shell.addSubInterface(...)`` exactly like the reference main window.
    """
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    rail = FluentNavRail(container)
    stack = QStackedWidget(container)
    stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    layout.addWidget(rail, 0)
    layout.addWidget(stack, 1)

    shell = NavigationShell(rail, stack)
    return container, shell


def wrap_scrollable(page: QWidget) -> QWidget:
    """Wrap a page in a borderless scroll area (reference pages scroll)."""
    from PyQt6.QtWidgets import QScrollArea

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setWidget(page)
    return scroll


def current_key(shell: Any) -> str | None:
    """Key of the currently visible page (``None`` when empty)."""
    try:
        widget = shell.stack.currentWidget()
    except Exception:
        return None
    for key in shell.keys():
        if shell.page(key) is widget:
            return key
    return None
