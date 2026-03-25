from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from upbit_autotrader.core.config import Config


def build_preset_group(self):
    group = QGroupBox("📋 전략 프리셋")
    layout = QVBoxLayout()
    btn_row = QHBoxLayout()

    btn_aggressive = QPushButton("🔥 공격적")
    btn_aggressive.setToolTip(Config.DEFAULT_PRESETS["aggressive"]["description"])
    btn_aggressive.clicked.connect(lambda: self.apply_preset("aggressive"))
    btn_row.addWidget(btn_aggressive)

    btn_normal = QPushButton("⚖️ 표준")
    btn_normal.setToolTip(Config.DEFAULT_PRESETS["normal"]["description"])
    btn_normal.clicked.connect(lambda: self.apply_preset("normal"))
    btn_row.addWidget(btn_normal)

    btn_conservative = QPushButton("🛡️ 보수적")
    btn_conservative.setToolTip(Config.DEFAULT_PRESETS["conservative"]["description"])
    btn_conservative.clicked.connect(lambda: self.apply_preset("conservative"))
    btn_row.addWidget(btn_conservative)
    layout.addLayout(btn_row)

    manage_row = QHBoxLayout()
    self.lbl_current_preset = QLabel("💡 프리셋을 선택하거나 직접 값을 조정하세요")
    self.lbl_current_preset.setStyleSheet("color: #90e0ef; font-style: italic;")
    manage_row.addWidget(self.lbl_current_preset)
    manage_row.addStretch(1)

    btn_manage_presets = QPushButton("📁 프리셋 관리")
    btn_manage_presets.clicked.connect(self.open_preset_manager)
    manage_row.addWidget(btn_manage_presets)

    layout.addLayout(manage_row)
    group.setLayout(layout)
    return group
