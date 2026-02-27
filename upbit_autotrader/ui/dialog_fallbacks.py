"""Fallback dialog implementations used when primary dialog module import fails."""

from __future__ import annotations

import datetime
import json
import os
import re
from typing import Any, Dict, List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
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

try:
    from upbit_autotrader.ui.dialogs import DARK_STYLESHEET
except Exception:
    DARK_STYLESHEET = ""


class PresetManagerDialog(QDialog):
    def __init__(self, parent=None, current_values: Dict[str, Any] | None = None):
        super().__init__(parent)
        self.current_values = current_values or {}
        self.presets = self.load_presets()
        self.selected_preset = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Preset Manager")
        self.setFixedSize(700, 600)
        self.setStyleSheet(DARK_STYLESHEET)

        layout = QVBoxLayout(self)

        group_list = QGroupBox("Saved Presets")
        list_layout = QVBoxLayout()
        self.preset_list = QListWidget()
        self.preset_list.itemClicked.connect(self.on_preset_selected)
        list_layout.addWidget(self.preset_list)

        self.detail_label = QLabel("Select a preset to view details.")
        self.detail_label.setWordWrap(True)
        list_layout.addWidget(self.detail_label)
        group_list.setLayout(list_layout)
        layout.addWidget(group_list)

        group_new = QGroupBox("Save Current Values")
        new_layout = QHBoxLayout()
        new_layout.addWidget(QLabel("Name:"))
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Preset name")
        new_layout.addWidget(self.input_name)
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save_current_preset)
        new_layout.addWidget(btn_save)
        group_new.setLayout(new_layout)
        layout.addWidget(group_new)

        btn_layout = QHBoxLayout()
        btn_delete = QPushButton("Delete")
        btn_delete.clicked.connect(self.delete_preset)
        btn_layout.addWidget(btn_delete)
        btn_layout.addStretch(1)

        btn_apply = QPushButton("Apply")
        btn_apply.clicked.connect(self.apply_preset)
        btn_layout.addWidget(btn_apply)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        self.refresh_preset_list()

    def load_presets(self):
        presets = dict(Config.DEFAULT_PRESETS)
        if os.path.exists(Config.PRESETS_FILE):
            try:
                with open(Config.PRESETS_FILE, "r", encoding="utf-8") as f:
                    user_presets = json.load(f)
                if isinstance(user_presets, dict):
                    presets.update(user_presets)
            except Exception:
                pass
        return presets

    def save_presets_to_file(self):
        user_presets = {k: v for k, v in self.presets.items() if k not in Config.DEFAULT_PRESETS}
        try:
            with open(Config.PRESETS_FILE, "w", encoding="utf-8") as f:
                json.dump(user_presets, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def refresh_preset_list(self):
        self.preset_list.clear()
        for key, preset in self.presets.items():
            name = preset.get("name", key)
            is_default = key in Config.DEFAULT_PRESETS
            prefix = "[default] " if is_default else "[user] "
            item = QListWidgetItem(prefix + str(name))
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setForeground(QColor("#93c5fd") if is_default else QColor("#fda4af"))
            self.preset_list.addItem(item)

    def on_preset_selected(self, item):
        key = item.data(Qt.ItemDataRole.UserRole)
        preset = self.presets.get(key, {})
        desc = preset.get("description", "No description")
        details = (
            f"<b>{preset.get('name', key)}</b><br><br>"
            f"{desc}<br><br>"
            f"k: {preset.get('k', '-')}<br>"
            f"ts_start: {preset.get('ts_start', '-')}%<br>"
            f"ts_stop: {preset.get('ts_stop', '-')}%<br>"
            f"loss_cut: {preset.get('loss', '-')}%<br>"
            f"betting: {preset.get('betting', '-')}%<br>"
            f"rsi_upper: {preset.get('rsi_upper', '-')}<br>"
            f"max_holdings: {preset.get('max_holdings', '-')}<br>"
            f"engine_gate_policy: {preset.get('engine_gate_policy', '-')}<br>"
            f"paper_trading: {'ON' if preset.get('paper_trading') else 'OFF'}"
        )
        self.detail_label.setText(details)

    def save_current_preset(self):
        name = self.input_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter preset name.")
            return

        key = "custom_" + re.sub(r"\s+", "_", name.lower())
        if key in Config.DEFAULT_PRESETS:
            QMessageBox.warning(self, "Warning", "Name conflicts with default preset.")
            return

        self.presets[key] = {
            "name": f"Custom {name}",
            "description": f"Saved on {datetime.datetime.now().strftime('%Y-%m-%d')}",
            **self.current_values,
        }
        self.save_presets_to_file()
        self.refresh_preset_list()
        self.input_name.clear()
        QMessageBox.information(self, "Saved", f"Preset '{name}' saved.")

    def delete_preset(self):
        item = self.preset_list.currentItem()
        if not item:
            return

        key = item.data(Qt.ItemDataRole.UserRole)
        if key in Config.DEFAULT_PRESETS:
            QMessageBox.warning(self, "Warning", "Default presets cannot be deleted.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm",
            f"Delete '{self.presets[key].get('name', key)}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            del self.presets[key]
            self.save_presets_to_file()
            self.refresh_preset_list()
            self.detail_label.setText("Select a preset to view details.")

    def apply_preset(self):
        item = self.preset_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Warning", "Select preset to apply.")
            return

        key = item.data(Qt.ItemDataRole.UserRole)
        self.selected_preset = self.presets.get(key)
        self.accept()

    def get_selected_preset(self):
        return self.selected_preset


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Help")
        self.setFixedSize(800, 700)
        self.setStyleSheet(DARK_STYLESHEET)

        layout = QVBoxLayout(self)
        tabs = QTabWidget()

        content = getattr(Config, "HELP_CONTENT", {}) or {}

        quick_text = QTextEdit()
        quick_text.setReadOnly(True)
        quick_text.setHtml(self.markdown_to_html(str(content.get("quick_start", "No quick start guide."))))
        tabs.addTab(quick_text, "Quick Start")

        strategy_text = QTextEdit()
        strategy_text.setReadOnly(True)
        strategy_text.setHtml(self.markdown_to_html(str(content.get("strategy", "No strategy guide."))))
        tabs.addTab(strategy_text, "Strategy")

        faq_text = QTextEdit()
        faq_text.setReadOnly(True)
        faq_text.setHtml(self.markdown_to_html(str(content.get("faq", "No FAQ content."))))
        tabs.addTab(faq_text, "FAQ")

        layout.addWidget(tabs)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

    @staticmethod
    def markdown_to_html(text: str) -> str:
        html: List[str] = ["<div style='line-height:1.6'>"]
        for line in text.splitlines():
            s = line.strip()
            if not s:
                html.append("<br>")
            elif s.startswith("### "):
                html.append(f"<h3>{s[4:]}</h3>")
            elif s.startswith("## "):
                html.append(f"<h2>{s[3:]}</h2>")
            elif s.startswith("# "):
                html.append(f"<h1>{s[2:]}</h1>")
            elif s.startswith("- ") or s.startswith("* "):
                html.append(f"<li>{s[2:]}</li>")
            else:
                html.append(f"<p>{s}</p>")
        html.append("</div>")
        return "".join(html)


class SettingsDialog(QDialog):
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.settings = settings or {}
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("System Settings")
        self.setFixedSize(550, 400)
        self.setStyleSheet(DARK_STYLESHEET)

        layout = QVBoxLayout(self)

        group_tray = QGroupBox("Tray")
        tray_layout = QVBoxLayout()

        self.chk_minimize_to_tray = QCheckBox("Minimize to tray on close")
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

        self.chk_auto_connect = QCheckBox("Auto-connect API")
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

    def get_settings(self):
        return {
            "minimize_to_tray": self.chk_minimize_to_tray.isChecked(),
            "show_tray_notifications": self.chk_show_tray_notifications.isChecked(),
            "run_at_startup": self.chk_run_at_startup.isChecked(),
            "start_minimized": self.chk_start_minimized.isChecked(),
            "auto_connect": self.chk_auto_connect.isChecked(),
            "sound_enabled": self.chk_sound_enabled.isChecked(),
        }

