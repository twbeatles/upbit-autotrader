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



DARK_STYLESHEET = """
QWidget {
    background-color: #0f172a;
    color: #e2e8f0;
    font-family: 'Malgun Gothic';
}
QGroupBox {
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 8px;
    padding-top: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
    color: #93c5fd;
}
QLineEdit, QTextEdit, QListWidget, QComboBox {
    background-color: #111827;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px;
}
QPushButton {
    background-color: #1d4ed8;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    color: #f8fafc;
}
QPushButton:disabled {
    background-color: #475569;
    color: #cbd5e1;
}
QPushButton:hover:!disabled {
    background-color: #2563eb;
}
"""
