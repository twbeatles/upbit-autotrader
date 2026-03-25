from PyQt6.QtWidgets import QCheckBox, QDoubleSpinBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QSpinBox

from upbit_autotrader.core.config import Config


def build_meta_group(self):
    group = QGroupBox("🧠 메타 시그널 / 가중치 리밸런싱")
    layout = QGridLayout()

    self.chk_use_meta_signal = QCheckBox("메타 시그널 게이트 사용")
    self.chk_use_meta_signal.setChecked(Config.DEFAULT_USE_META_SIGNAL)
    self.chk_use_meta_signal.setToolTip(Config.TOOLTIPS.get("meta_signal", ""))
    layout.addWidget(self.chk_use_meta_signal, 0, 0, 1, 2)

    layout.addWidget(QLabel("최소 기대값(%):"), 0, 2)
    self.spin_meta_min_expectancy = QDoubleSpinBox()
    self.spin_meta_min_expectancy.setRange(-10.0, 20.0)
    self.spin_meta_min_expectancy.setSingleStep(0.1)
    self.spin_meta_min_expectancy.setValue(Config.DEFAULT_META_MIN_EXPECTANCY)
    self.spin_meta_min_expectancy.setToolTip(Config.TOOLTIPS.get("meta_min_expectancy", ""))
    layout.addWidget(self.spin_meta_min_expectancy, 0, 3)

    layout.addWidget(QLabel("메타 점수 임계:"), 0, 4)
    self.spin_meta_score_threshold = QSpinBox()
    self.spin_meta_score_threshold.setRange(0, 100)
    self.spin_meta_score_threshold.setValue(int(Config.DEFAULT_META_SCORE_THRESHOLD))
    self.spin_meta_score_threshold.setToolTip(Config.TOOLTIPS.get("meta_score_threshold", ""))
    layout.addWidget(self.spin_meta_score_threshold, 0, 5)

    self.chk_weight_rebalance_daily = QCheckBox("전략 가중치 일일 리밸런싱")
    self.chk_weight_rebalance_daily.setChecked(Config.DEFAULT_WEIGHT_REBALANCE_DAILY)
    self.chk_weight_rebalance_daily.setToolTip(Config.TOOLTIPS.get("weight_rebalance_daily", ""))
    layout.addWidget(self.chk_weight_rebalance_daily, 1, 0, 1, 2)

    layout.addWidget(QLabel("가중치 최소/최대:"), 1, 2)
    w_row = QHBoxLayout()
    self.spin_weight_min = QDoubleSpinBox()
    self.spin_weight_min.setRange(0.1, 2.0)
    self.spin_weight_min.setSingleStep(0.1)
    self.spin_weight_min.setValue(Config.DEFAULT_WEIGHT_MIN)
    w_row.addWidget(self.spin_weight_min)
    self.spin_weight_max = QDoubleSpinBox()
    self.spin_weight_max.setRange(0.2, 3.0)
    self.spin_weight_max.setSingleStep(0.1)
    self.spin_weight_max.setValue(Config.DEFAULT_WEIGHT_MAX)
    w_row.addWidget(self.spin_weight_max)
    layout.addLayout(w_row, 1, 3, 1, 3)

    group.setLayout(layout)
    return group
