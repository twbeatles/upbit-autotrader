from PyQt6.QtWidgets import QCheckBox, QDoubleSpinBox, QGridLayout, QGroupBox, QLabel

from upbit_autotrader.core.config import Config


def build_paper_group(self):
    group = QGroupBox("🧪 페이퍼 트레이딩")
    layout = QGridLayout()
    self.chk_paper_trading = QCheckBox("페이퍼 트레이딩 사용")
    self.chk_paper_trading.setChecked(Config.DEFAULT_PAPER_TRADING)
    self.chk_paper_trading.setToolTip(Config.TOOLTIPS.get("paper_trading", ""))
    layout.addWidget(self.chk_paper_trading, 0, 0, 1, 2)
    self.chk_paper_trading.toggled.connect(lambda _checked: self.refresh_trade_action_buttons())

    self.chk_paper_allow_without_login = QCheckBox("무로그인 시작 허용")
    self.chk_paper_allow_without_login.setChecked(Config.DEFAULT_PAPER_ALLOW_WITHOUT_LOGIN)
    self.chk_paper_allow_without_login.setToolTip(Config.TOOLTIPS.get("paper_allow_without_login", ""))
    layout.addWidget(self.chk_paper_allow_without_login, 0, 2, 1, 2)
    self.chk_paper_allow_without_login.toggled.connect(lambda _checked: self.refresh_trade_action_buttons())

    layout.addWidget(QLabel("수수료(bps):"), 1, 0)
    self.spin_paper_fee_bps = QDoubleSpinBox()
    self.spin_paper_fee_bps.setRange(0.0, 100.0)
    self.spin_paper_fee_bps.setSingleStep(0.5)
    self.spin_paper_fee_bps.setValue(Config.DEFAULT_PAPER_FEE_BPS)
    layout.addWidget(self.spin_paper_fee_bps, 1, 1)

    layout.addWidget(QLabel("슬리피지(bps):"), 1, 2)
    self.spin_paper_slippage_bps = QDoubleSpinBox()
    self.spin_paper_slippage_bps.setRange(0.0, 200.0)
    self.spin_paper_slippage_bps.setSingleStep(0.5)
    self.spin_paper_slippage_bps.setValue(Config.DEFAULT_PAPER_SLIPPAGE_BPS)
    layout.addWidget(self.spin_paper_slippage_bps, 1, 3)

    layout.addWidget(QLabel("초기 시드(KRW):"), 2, 0)
    self.spin_paper_seed_krw = QDoubleSpinBox()
    self.spin_paper_seed_krw.setRange(100000.0, 1000000000.0)
    self.spin_paper_seed_krw.setSingleStep(100000.0)
    self.spin_paper_seed_krw.setDecimals(0)
    self.spin_paper_seed_krw.setValue(float(Config.DEFAULT_PAPER_SEED_KRW))
    self.spin_paper_seed_krw.setToolTip(Config.TOOLTIPS.get("paper_seed_krw", ""))
    layout.addWidget(self.spin_paper_seed_krw, 2, 1)
    group.setLayout(layout)
    return group
