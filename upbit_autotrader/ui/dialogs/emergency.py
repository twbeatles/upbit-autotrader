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
from upbit_autotrader.ui.components.status_badge import set_status_badge

class EmergencyCloseDialog(QDialog):
    """Confirm emergency close-all operation."""

    def __init__(self, parent=None, holdings: Iterable[Dict[str, Any]] | None = None):
        super().__init__(parent)
        self.holdings = list(holdings or [])
        self.init_ui()

    def init_ui(self) -> None:
        self.setWindowTitle("Emergency Close")
        self.setFixedSize(520, 420)
        self.setStyleSheet(DARK_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        warning = QLabel("All holdings will be sold with market orders immediately.")
        set_status_badge(warning, "error")
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(warning)

        group = QGroupBox(f"Positions ({len(self.holdings)})")
        group_layout = QVBoxLayout()
        list_widget = QListWidget()

        if self.holdings:
            for h in self.holdings:
                ticker = str(h.get("ticker", ""))
                qty = float(h.get("qty", 0.0) or 0.0)
                pnl = float(h.get("pnl", 0.0) or 0.0)
                value = float(h.get("value", 0.0) or 0.0)
                item = QListWidgetItem(f"{ticker}: {qty:.8f} | {value:,.0f} KRW | {pnl:+.2f}%")
                item.setForeground(QColor("#34d399") if pnl >= 0 else QColor("#f87171"))
                list_widget.addItem(item)
        else:
            list_widget.addItem("No holdings")

        group_layout.addWidget(list_widget)
        group.setLayout(group_layout)
        layout.addWidget(group)

        self.chk_confirm = QCheckBox("I understand the risk and want to execute emergency close")
        layout.addWidget(self.chk_confirm)

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_layout.addStretch(1)

        self.btn_confirm = QPushButton("Execute")
        self.btn_confirm.setProperty("destructive", True)
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_confirm)

        layout.addLayout(btn_layout)

        self.chk_confirm.stateChanged.connect(
            lambda _state: self.btn_confirm.setEnabled(self.chk_confirm.isChecked())
        )
