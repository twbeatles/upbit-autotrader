"""Empty-state placeholder for tables/lists (rules sections 14/17)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from upbit_autotrader.ui import design_tokens as tokens


class EmptyState(QWidget):
    """Centered ``title`` + ``hint`` placeholder shown instead of bare emptiness."""

    def __init__(self, title: str, hint: str = "", parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            tokens.SPACE_LG, tokens.SPACE_LG, tokens.SPACE_LG, tokens.SPACE_LG
        )
        layout.setSpacing(tokens.SPACE_XS)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("emptyStateTitle")
        title_font = self.title_label.font()
        title_font.setPointSize(tokens.FONT_SECTION_TITLE)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        self.hint_label = QLabel(hint)
        self.hint_label.setObjectName("emptyStateHint")
        hint_font = self.hint_label.font()
        hint_font.setPointSize(tokens.FONT_SECONDARY)
        self.hint_label.setFont(hint_font)
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setWordWrap(True)
        self.hint_label.setVisible(bool(hint))
        layout.addWidget(self.hint_label)
