"""Semantic status badge (rules section 7).

Replaces scattered ``setStyleSheet("color: #...")`` calls on status labels
with a single helper fed by design tokens.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel

from upbit_autotrader.ui import design_tokens as tokens
from upbit_autotrader.ui.theme import is_dark_mode


class StatusBadge(QLabel):
    """Small semantic status label: kind=success|warning|error|info|neutral."""

    def __init__(self, text: str = "", kind: str = "neutral", parent=None) -> None:
        super().__init__(text, parent)
        self._kind = kind
        self.refresh()

    def set_kind(self, kind: str) -> None:
        self._kind = kind
        self.refresh()

    def kind(self) -> str:
        return self._kind

    def refresh(self) -> None:
        color = tokens.status_color(self._kind, is_dark_mode())
        font = self.font()
        font.setBold(True)
        self.setFont(font)
        self.setStyleSheet(f"color: {color}; background: transparent; border: none;")


def set_status_badge(label: QLabel, kind: str) -> None:
    """Apply semantic coloring to an existing status ``QLabel`` in place."""
    color = tokens.status_color(kind, is_dark_mode())
    font = label.font()
    font.setBold(True)
    label.setFont(font)
    try:
        label.setStyleSheet(f"color: {color}; background: transparent; border: none;")
    except Exception:
        pass
