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
from upbit_autotrader.ui import design_tokens as tokens
from upbit_autotrader.ui.theme import is_dark_mode

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
        self.detail_label.setStyleSheet(f"padding: {tokens.SPACE_XS}px; background: {tokens.palette(is_dark_mode())['surface_alt']}; border-radius: 6px;")
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
