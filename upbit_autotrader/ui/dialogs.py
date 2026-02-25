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

from upbit_config import Config


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


class PresetManagerDialog(QDialog):
    """Manage strategy presets."""

    def __init__(self, parent=None, current_values: Dict[str, Any] | None = None):
        super().__init__(parent)
        self.current_values = current_values or {}
        self.presets = self.load_presets()
        self.selected_preset = None
        self.init_ui()

    def init_ui(self) -> None:
        self.setWindowTitle("Preset Manager")
        self.setFixedSize(700, 600)
        self.setStyleSheet(DARK_STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        group_list = QGroupBox("Saved Presets")
        list_layout = QVBoxLayout()

        self.preset_list = QListWidget()
        self.preset_list.itemClicked.connect(self.on_preset_selected)
        list_layout.addWidget(self.preset_list)

        self.detail_label = QLabel("Select a preset to view details.")
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet("padding: 8px; background: #1e293b; border-radius: 6px;")
        list_layout.addWidget(self.detail_label)

        group_list.setLayout(list_layout)
        layout.addWidget(group_list)

        group_new = QGroupBox("Save Current Values")
        new_layout = QHBoxLayout()
        new_layout.addWidget(QLabel("Name:"))

        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("e.g. scalping-night")
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

    def load_presets(self) -> Dict[str, Dict[str, Any]]:
        presets = dict(Config.DEFAULT_PRESETS)
        if not os.path.exists(Config.PRESETS_FILE):
            return presets

        try:
            with open(Config.PRESETS_FILE, "r", encoding="utf-8") as f:
                user_presets = json.load(f)
            if isinstance(user_presets, dict):
                presets.update(user_presets)
        except Exception:
            pass
        return presets

    def save_presets_to_file(self) -> None:
        user_presets = {k: v for k, v in self.presets.items() if k not in Config.DEFAULT_PRESETS}
        try:
            with open(Config.PRESETS_FILE, "w", encoding="utf-8") as f:
                json.dump(user_presets, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def refresh_preset_list(self) -> None:
        self.preset_list.clear()
        for key, preset in self.presets.items():
            name = str(preset.get("name", key))
            is_default = key in Config.DEFAULT_PRESETS
            prefix = "[default] " if is_default else "[user] "
            item = QListWidgetItem(prefix + name)
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setForeground(QColor("#93c5fd") if is_default else QColor("#fda4af"))
            self.preset_list.addItem(item)

    def on_preset_selected(self, item: QListWidgetItem) -> None:
        key = item.data(Qt.ItemDataRole.UserRole)
        preset = self.presets.get(key, {})
        lines = [
            f"<b>{preset.get('name', key)}</b>",
            "",
            str(preset.get("description", "No description")),
            "",
            "<b>Core</b>",
            f"k: {preset.get('k', '-')}",
            f"ts_start: {preset.get('ts_start', '-')}%",
            f"ts_stop: {preset.get('ts_stop', '-')}%",
            f"loss_cut: {preset.get('loss', '-')}%",
            f"betting: {preset.get('betting', '-')}%",
            f"rsi_upper: {preset.get('rsi_upper', '-')}",
            f"max_holdings: {preset.get('max_holdings', '-')}",
            "",
            "<b>Engine</b>",
            f"use_strategy_engine: {'ON' if preset.get('use_strategy_engine') else 'OFF'}",
            f"strategy_mode: {preset.get('strategy_mode', '-')}",
            f"single_strategy: {preset.get('single_strategy', '-')}",
            f"engine_gate_policy: {preset.get('engine_gate_policy', '-')}",
            f"ensemble_threshold: {preset.get('ensemble_threshold', '-')}",
            "",
            "<b>Paper</b>",
            f"paper_trading: {'ON' if preset.get('paper_trading') else 'OFF'}",
        ]
        self.detail_label.setText("<br>".join(lines))

    def save_current_preset(self) -> None:
        name = self.input_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter a preset name.")
            return

        key = "custom_" + re.sub(r"\s+", "_", name.lower())
        if key in Config.DEFAULT_PRESETS:
            QMessageBox.warning(self, "Warning", "This name conflicts with default preset key.")
            return

        self.presets[key] = {
            "name": f"Custom {name}",
            "description": f"User preset saved at {datetime.datetime.now().strftime('%Y-%m-%d')}",
            **self.current_values,
        }
        self.save_presets_to_file()
        self.refresh_preset_list()
        self.input_name.clear()
        QMessageBox.information(self, "Saved", f"Preset '{name}' saved.")

    def delete_preset(self) -> None:
        item = self.preset_list.currentItem()
        if not item:
            return

        key = item.data(Qt.ItemDataRole.UserRole)
        if key in Config.DEFAULT_PRESETS:
            QMessageBox.warning(self, "Warning", "Default presets cannot be deleted.")
            return

        name = self.presets.get(key, {}).get("name", key)
        reply = QMessageBox.question(
            self,
            "Confirm",
            f"Delete preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.presets.pop(key, None)
        self.save_presets_to_file()
        self.refresh_preset_list()
        self.detail_label.setText("Select a preset to view details.")

    def apply_preset(self) -> None:
        item = self.preset_list.currentItem()
        if not item:
            QMessageBox.warning(self, "Warning", "Select a preset to apply.")
            return

        key = item.data(Qt.ItemDataRole.UserRole)
        self.selected_preset = self.presets.get(key)
        self.accept()

    def get_selected_preset(self):
        return self.selected_preset


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
        warning.setStyleSheet("color: #f87171; font-weight: bold;")
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
        self.btn_confirm.setStyleSheet("background-color: #dc2626; font-weight: bold;")
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_confirm)

        layout.addLayout(btn_layout)

        self.chk_confirm.stateChanged.connect(
            lambda _state: self.btn_confirm.setEnabled(self.chk_confirm.isChecked())
        )
