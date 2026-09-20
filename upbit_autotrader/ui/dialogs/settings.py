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

class SettingsDialog(QDialog):
    """System settings dialog."""

    def __init__(self, parent=None, settings: Dict[str, Any] | None = None):
        super().__init__(parent)
        self.settings = dict(settings or {})
        self.init_ui()

    def init_ui(self) -> None:
        self.setWindowTitle("System Settings")
        self.setFixedSize(560, 420)
        self.setStyleSheet(DARK_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        group_tray = QGroupBox("Tray")
        tray_layout = QVBoxLayout()
        self.chk_minimize_to_tray = QCheckBox("Minimize to tray when closing window")
        self.chk_minimize_to_tray.setChecked(bool(self.settings.get("minimize_to_tray", True)))
        tray_layout.addWidget(self.chk_minimize_to_tray)

        self.chk_show_tray_notifications = QCheckBox("Show tray notifications")
        self.chk_show_tray_notifications.setChecked(bool(self.settings.get("show_tray_notifications", True)))
        tray_layout.addWidget(self.chk_show_tray_notifications)
        group_tray.setLayout(tray_layout)
        layout.addWidget(group_tray)

        group_startup = QGroupBox("Startup")
        startup_layout = QVBoxLayout()
        self.chk_run_at_startup = QCheckBox("Run at Windows startup")
        self.chk_run_at_startup.setChecked(bool(self.settings.get("run_at_startup", False)))
        startup_layout.addWidget(self.chk_run_at_startup)

        self.chk_start_minimized = QCheckBox("Start minimized")
        self.chk_start_minimized.setChecked(bool(self.settings.get("start_minimized", False)))
        startup_layout.addWidget(self.chk_start_minimized)

        self.chk_auto_connect = QCheckBox("Auto-connect API on startup")
        self.chk_auto_connect.setChecked(bool(self.settings.get("auto_connect", False)))
        startup_layout.addWidget(self.chk_auto_connect)

        group_startup.setLayout(startup_layout)
        layout.addWidget(group_startup)

        group_misc = QGroupBox("Misc")
        misc_layout = QVBoxLayout()
        self.chk_sound_enabled = QCheckBox("Enable sound alerts")
        self.chk_sound_enabled.setChecked(bool(self.settings.get("sound_enabled", True)))
        misc_layout.addWidget(self.chk_sound_enabled)
        group_misc.setLayout(misc_layout)
        layout.addWidget(group_misc)

        layout.addStretch(1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)

        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def get_settings(self) -> Dict[str, Any]:
        return {
            "minimize_to_tray": self.chk_minimize_to_tray.isChecked(),
            "show_tray_notifications": self.chk_show_tray_notifications.isChecked(),
            "run_at_startup": self.chk_run_at_startup.isChecked(),
            "start_minimized": self.chk_start_minimized.isChecked(),
            "auto_connect": self.chk_auto_connect.isChecked(),
            "sound_enabled": self.chk_sound_enabled.isChecked(),
        }
