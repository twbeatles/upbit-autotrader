"""Title + secondary-text section header (rules section 6)."""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from upbit_autotrader.ui import design_tokens as tokens


class SectionHeader(QWidget):
    """Compact ``title`` + one-line ``subtitle`` header for page sections."""

    def __init__(self, title: str, subtitle: str = "", parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(tokens.SPACE_XXS)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionTitle")
        title_font = self.title_label.font()
        title_font.setPointSize(tokens.FONT_SECTION_TITLE)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("sectionSubtitle")
        sub_font = self.subtitle_label.font()
        sub_font.setPointSize(tokens.FONT_SECONDARY)
        self.subtitle_label.setFont(sub_font)
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setVisible(bool(subtitle))
        layout.addWidget(self.subtitle_label)
