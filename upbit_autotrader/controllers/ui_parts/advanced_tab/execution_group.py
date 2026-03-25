from PyQt6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QGroupBox, QLabel, QSpinBox

from upbit_autotrader.core.config import Config


def build_execution_group(self):
    group = QGroupBox("⚙️ 실행 모델 / TWAP")
    layout = QGridLayout()

    self.chk_use_execution_model = QCheckBox("실행 모델 사용")
    self.chk_use_execution_model.setChecked(Config.DEFAULT_USE_EXECUTION_MODEL)
    self.chk_use_execution_model.setToolTip(Config.TOOLTIPS.get("execution_model", ""))
    layout.addWidget(self.chk_use_execution_model, 0, 0, 1, 2)

    layout.addWidget(QLabel("실행 모드:"), 0, 2)
    self.combo_execution_mode = QComboBox()
    self.combo_execution_mode.addItem("일반 시장가", "single_market")
    self.combo_execution_mode.addItem("TWAP 분할", "twap_market")
    idx_exec = self.combo_execution_mode.findData(Config.DEFAULT_EXECUTION_MODE)
    if idx_exec >= 0:
        self.combo_execution_mode.setCurrentIndex(idx_exec)
    layout.addWidget(self.combo_execution_mode, 0, 3)

    layout.addWidget(QLabel("슬리피지 가드(bps):"), 1, 0)
    self.spin_expected_slippage_guard_bps = QDoubleSpinBox()
    self.spin_expected_slippage_guard_bps.setRange(1.0, 300.0)
    self.spin_expected_slippage_guard_bps.setSingleStep(1.0)
    self.spin_expected_slippage_guard_bps.setValue(Config.DEFAULT_EXPECTED_SLIPPAGE_GUARD_BPS)
    self.spin_expected_slippage_guard_bps.setToolTip(Config.TOOLTIPS.get("expected_slippage_guard_bps", ""))
    layout.addWidget(self.spin_expected_slippage_guard_bps, 1, 1)

    layout.addWidget(QLabel("TWAP 분할 수:"), 1, 2)
    self.spin_twap_slices = QSpinBox()
    self.spin_twap_slices.setRange(2, 20)
    self.spin_twap_slices.setValue(Config.DEFAULT_TWAP_SLICES)
    layout.addWidget(self.spin_twap_slices, 1, 3)

    layout.addWidget(QLabel("TWAP 간격(초):"), 1, 4)
    self.spin_twap_interval_sec = QSpinBox()
    self.spin_twap_interval_sec.setRange(1, 120)
    self.spin_twap_interval_sec.setValue(Config.DEFAULT_TWAP_INTERVAL_SEC)
    layout.addWidget(self.spin_twap_interval_sec, 1, 5)

    group.setLayout(layout)
    return group
