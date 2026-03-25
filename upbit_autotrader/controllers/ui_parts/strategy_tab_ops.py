from PyQt6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget

from upbit_autotrader.core.config import Config


def create_strategy_tab(self):
    widget = QWidget()
    layout = QGridLayout(widget)
    layout.setSpacing(12)
    layout.setContentsMargins(15, 15, 15, 15)

    layout.addWidget(QLabel("📋 감시 코인 (콤마 구분):"), 0, 0)
    self.input_coins = QLineEdit(Config.DEFAULT_COINS)
    self.input_coins.setPlaceholderText("예: KRW-BTC,KRW-ETH,KRW-XRP")
    self.input_coins.setToolTip(Config.TOOLTIPS["coins"])
    layout.addWidget(self.input_coins, 0, 1, 1, 5)

    layout.addWidget(QLabel("🕐 캔들 간격:"), 1, 0)
    self.combo_candle = QComboBox()
    self.combo_candle.addItems(Config.CANDLE_INTERVALS.keys())
    self.combo_candle.setCurrentText(Config.DEFAULT_CANDLE)
    self.combo_candle.setToolTip(Config.TOOLTIPS["candle"])
    layout.addWidget(self.combo_candle, 1, 1)

    layout.addWidget(QLabel("💵 종목당 투자비중:"), 1, 2)
    self.spin_betting = QDoubleSpinBox()
    self.spin_betting.setRange(1, 100)
    self.spin_betting.setValue(Config.DEFAULT_BETTING_RATIO)
    self.spin_betting.setSuffix(" %")
    self.spin_betting.setToolTip(Config.TOOLTIPS["betting"])
    layout.addWidget(self.spin_betting, 1, 3)

    layout.addWidget(QLabel("📐 변동성 K값:"), 1, 4)
    self.spin_k = QDoubleSpinBox()
    self.spin_k.setRange(0.1, 1.0)
    self.spin_k.setSingleStep(0.1)
    self.spin_k.setValue(Config.DEFAULT_K_VALUE)
    self.spin_k.setToolTip(Config.TOOLTIPS["k_value"])
    layout.addWidget(self.spin_k, 1, 5)

    layout.addWidget(QLabel("🎯 TS 발동 수익률:"), 2, 0)
    self.spin_ts_start = QDoubleSpinBox()
    self.spin_ts_start.setRange(0.5, 30.0)
    self.spin_ts_start.setValue(Config.DEFAULT_TS_START)
    self.spin_ts_start.setSuffix(" %")
    self.spin_ts_start.setToolTip(Config.TOOLTIPS["ts_start"])
    layout.addWidget(self.spin_ts_start, 2, 1)

    layout.addWidget(QLabel("📉 TS 하락폭:"), 2, 2)
    self.spin_ts_stop = QDoubleSpinBox()
    self.spin_ts_stop.setRange(0.5, 15.0)
    self.spin_ts_stop.setValue(Config.DEFAULT_TS_STOP)
    self.spin_ts_stop.setSuffix(" %")
    self.spin_ts_stop.setToolTip(Config.TOOLTIPS["ts_stop"])
    layout.addWidget(self.spin_ts_stop, 2, 3)

    layout.addWidget(QLabel("🛑 절대 손절률:"), 2, 4)
    self.spin_loss = QDoubleSpinBox()
    self.spin_loss.setRange(0.5, 20.0)
    self.spin_loss.setValue(Config.DEFAULT_LOSS_CUT)
    self.spin_loss.setSuffix(" %")
    self.spin_loss.setToolTip(Config.TOOLTIPS["loss_cut"])
    layout.addWidget(self.spin_loss, 2, 5)

    batch_layout = QHBoxLayout()
    batch_layout.setSpacing(10)

    self.btn_batch_sell = QPushButton("📤 일괄 매도")
    self.btn_batch_sell.setMinimumSize(120, 40)
    self.btn_batch_sell.setStyleSheet("QPushButton { background-color: #e74c3c; } QPushButton:hover { background-color: #c0392b; }")
    self.btn_batch_sell.setToolTip("현재 보유 중인 모든 코인을 시장가로 일괄 매도합니다.")
    self.btn_batch_sell.clicked.connect(self.execute_batch_sell)
    self.btn_batch_sell.setEnabled(False)

    self.btn_batch_buy = QPushButton("📥 일괄 매수")
    self.btn_batch_buy.setMinimumSize(120, 40)
    self.btn_batch_buy.setStyleSheet("QPushButton { background-color: #27ae60; } QPushButton:hover { background-color: #1e8449; }")
    self.btn_batch_buy.setToolTip("입력된 코인들을 현재 시장가로 균등 분배 매수합니다.")
    self.btn_batch_buy.clicked.connect(self.execute_batch_buy)
    self.btn_batch_buy.setEnabled(False)

    self.chk_auto_start_after_batch = QCheckBox("완료 후 자동매매 시작")
    self.chk_auto_start_after_batch.setToolTip("일괄 매도/매수 완료 후 자동으로 알고리즘 매매를 시작합니다.")

    batch_layout.addWidget(self.btn_batch_sell)
    batch_layout.addWidget(self.btn_batch_buy)
    batch_layout.addWidget(self.chk_auto_start_after_batch)
    batch_layout.addStretch(1)
    layout.addLayout(batch_layout, 3, 0, 1, 6)

    btn_layout = QHBoxLayout()
    btn_layout.setSpacing(10)
    self.btn_save = QPushButton("💾 설정 저장")
    self.btn_save.clicked.connect(self.save_settings)

    self.btn_start = QPushButton("🚀 전략 분석 및 매매 시작")
    self.btn_start.setObjectName("startBtn")
    self.btn_start.setMinimumSize(250, 50)
    self.btn_start.clicked.connect(self.start_trading)
    self.btn_start.setEnabled(False)

    self.btn_stop = QPushButton("⏹️ 매매 중지")
    self.btn_stop.setObjectName("stopBtn")
    self.btn_stop.setMinimumSize(120, 50)
    self.btn_stop.clicked.connect(self.stop_trading)
    self.btn_stop.setEnabled(False)

    btn_layout.addWidget(self.btn_save)
    btn_layout.addStretch(1)
    btn_layout.addWidget(self.btn_start)
    btn_layout.addWidget(self.btn_stop)
    layout.addLayout(btn_layout, 4, 0, 1, 6)
    return widget
