"""Primary dialog implementations for UI flows."""

from __future__ import annotations

import datetime
import json
import os
import re
from typing import Any, Dict, Iterable, List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
)

from upbit_autotrader.core.config import Config



from .styles import DARK_STYLESHEET

class HelpDialog(QDialog):
    """Simple tabbed help dialog using Config.HELP_CONTENT markdown text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self) -> None:
        self.setWindowTitle("Help")
        self.setFixedSize(800, 700)
        self.setStyleSheet(DARK_STYLESHEET)

        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        help_content = getattr(Config, "HELP_CONTENT", {}) or {}

        quick = QTextEdit()
        quick.setReadOnly(True)
        quick.setHtml(self.markdown_to_html(str(help_content.get("quick_start", "No quick start guide."))))
        tabs.addTab(quick, "Quick Start")

        strategy = QTextEdit()
        strategy.setReadOnly(True)
        strategy.setHtml(self.markdown_to_html(str(help_content.get("strategy", "No strategy guide."))))
        tabs.addTab(strategy, "Strategy")

        faq = QTextEdit()
        faq.setReadOnly(True)
        faq.setHtml(self.markdown_to_html(str(help_content.get("faq", "No FAQ content."))))
        tabs.addTab(faq, "FAQ")

        layout.addWidget(tabs)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

    @staticmethod
    def markdown_to_html(text: str) -> str:
        lines = text.splitlines()
        html_lines: List[str] = ["<div style='line-height:1.6'>"]

        for line in lines:
            s = line.strip()
            if not s:
                html_lines.append("<br>")
                continue
            if s.startswith("### "):
                html_lines.append(f"<h3>{s[4:]}</h3>")
                continue
            if s.startswith("## "):
                html_lines.append(f"<h2>{s[3:]}</h2>")
                continue
            if s.startswith("# "):
                html_lines.append(f"<h1>{s[2:]}</h1>")
                continue
            if s.startswith("- ") or s.startswith("* "):
                html_lines.append(f"<li>{s[2:]}</li>")
                continue
            html_lines.append(f"<p>{s}</p>")

        html_lines.append("</div>")
        return "".join(html_lines)
