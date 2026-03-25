from PyQt6.QtWidgets import QCheckBox, QDoubleSpinBox, QGridLayout, QGroupBox, QLabel, QSpinBox

from upbit_autotrader.core.config import Config


def build_rsi_group(self):
    group = QGroupBox("📈 RSI 필터")
    layout = QGridLayout()
    self.chk_use_rsi = QCheckBox("RSI 필터 사용")
    self.chk_use_rsi.setChecked(Config.DEFAULT_USE_RSI)
    layout.addWidget(self.chk_use_rsi, 0, 0, 1, 2)

    layout.addWidget(QLabel("RSI 상한선:"), 1, 0)
    self.spin_rsi_upper = QSpinBox()
    self.spin_rsi_upper.setRange(50, 90)
    self.spin_rsi_upper.setValue(Config.DEFAULT_RSI_UPPER)
    layout.addWidget(self.spin_rsi_upper, 1, 1)

    layout.addWidget(QLabel("RSI 기간:"), 1, 2)
    self.spin_rsi_period = QSpinBox()
    self.spin_rsi_period.setRange(5, 30)
    self.spin_rsi_period.setValue(Config.DEFAULT_RSI_PERIOD)
    layout.addWidget(self.spin_rsi_period, 1, 3)
    group.setLayout(layout)
    return group


def build_macd_group(self):
    group = QGroupBox("📉 MACD 필터")
    layout = QGridLayout()
    self.chk_use_macd = QCheckBox("MACD 필터 사용 (골든크로스 확인)")
    self.chk_use_macd.setChecked(Config.DEFAULT_USE_MACD)
    self.chk_use_macd.setToolTip("MACD가 Signal선 위에 있을 때만 매수합니다.\n상승 모멘텀을 확인하여 진입 정확도를 높입니다.")
    layout.addWidget(self.chk_use_macd, 0, 0, 1, 2)
    group.setLayout(layout)
    return group


def build_volume_group(self):
    group = QGroupBox("📊 거래량 필터")
    layout = QGridLayout()
    self.chk_use_volume = QCheckBox("거래량 필터 사용")
    self.chk_use_volume.setChecked(Config.DEFAULT_USE_VOLUME)
    self.chk_use_volume.setToolTip("평균 거래량 대비 현재 거래량이 충분할 때만 매수합니다.\n거래량이 수반되지 않은 가격 상승은 신뢰도가 낮습니다.")
    layout.addWidget(self.chk_use_volume, 0, 0, 1, 2)

    layout.addWidget(QLabel("거래량 배수:"), 1, 0)
    self.spin_volume_mult = QDoubleSpinBox()
    self.spin_volume_mult.setRange(1.0, 5.0)
    self.spin_volume_mult.setSingleStep(0.1)
    self.spin_volume_mult.setValue(Config.DEFAULT_VOLUME_MULTIPLIER)
    self.spin_volume_mult.setToolTip("현재 거래량 >= 평균 거래량 × 배수 일 때 진입\n예: 1.5 = 평균의 1.5배 이상")
    layout.addWidget(self.spin_volume_mult, 1, 1)
    group.setLayout(layout)
    return group
