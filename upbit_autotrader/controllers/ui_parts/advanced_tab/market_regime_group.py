from PyQt6.QtWidgets import QCheckBox, QDoubleSpinBox, QGridLayout, QGroupBox, QLabel, QSpinBox

from upbit_autotrader.core.config import Config


def build_market_regime_group(self):
    group = QGroupBox("🌐 시장 레짐 / 외부 신호")
    layout = QGridLayout()

    self.chk_use_market_regime_filter = QCheckBox("시장 레짐 필터 사용")
    self.chk_use_market_regime_filter.setChecked(Config.DEFAULT_USE_MARKET_REGIME_FILTER)
    self.chk_use_market_regime_filter.setToolTip(Config.TOOLTIPS.get("market_regime_filter", ""))
    layout.addWidget(self.chk_use_market_regime_filter, 0, 0, 1, 2)

    self.chk_use_market_regime_risk_scaling = QCheckBox("시장 레짐 비중 스케일링 사용")
    self.chk_use_market_regime_risk_scaling.setChecked(Config.DEFAULT_USE_MARKET_REGIME_RISK_SCALING)
    self.chk_use_market_regime_risk_scaling.setToolTip(Config.TOOLTIPS.get("market_regime_risk_scaling", ""))
    layout.addWidget(self.chk_use_market_regime_risk_scaling, 0, 2, 1, 2)

    layout.addWidget(QLabel("최소 레짐 점수:"), 1, 0)
    self.spin_market_regime_min_score = QDoubleSpinBox()
    self.spin_market_regime_min_score.setRange(0.0, 100.0)
    self.spin_market_regime_min_score.setSingleStep(1.0)
    self.spin_market_regime_min_score.setValue(Config.DEFAULT_MARKET_REGIME_MIN_SCORE)
    self.spin_market_regime_min_score.setToolTip(Config.TOOLTIPS.get("market_regime_min_score", ""))
    layout.addWidget(self.spin_market_regime_min_score, 1, 1)

    layout.addWidget(QLabel("갱신 주기(초):"), 1, 2)
    self.spin_market_regime_refresh_sec = QSpinBox()
    self.spin_market_regime_refresh_sec.setRange(5, 600)
    self.spin_market_regime_refresh_sec.setValue(int(Config.DEFAULT_MARKET_REGIME_REFRESH_SEC))
    self.spin_market_regime_refresh_sec.setToolTip(Config.TOOLTIPS.get("market_regime_refresh_sec", ""))
    layout.addWidget(self.spin_market_regime_refresh_sec, 1, 3)

    layout.addWidget(QLabel("상위 종목 수:"), 1, 4)
    self.spin_market_regime_top_n = QSpinBox()
    self.spin_market_regime_top_n.setRange(5, 100)
    self.spin_market_regime_top_n.setValue(int(Config.DEFAULT_MARKET_REGIME_TOP_N))
    self.spin_market_regime_top_n.setToolTip(Config.TOOLTIPS.get("market_regime_top_n", ""))
    layout.addWidget(self.spin_market_regime_top_n, 1, 5)

    self.chk_market_regime_use_fear_greed = QCheckBox("Fear & Greed 사용")
    self.chk_market_regime_use_fear_greed.setChecked(Config.DEFAULT_MARKET_REGIME_USE_FEAR_GREED)
    self.chk_market_regime_use_fear_greed.setToolTip(Config.TOOLTIPS.get("market_regime_use_fear_greed", ""))
    layout.addWidget(self.chk_market_regime_use_fear_greed, 2, 0, 1, 2)

    self.chk_market_regime_use_etf_flow = QCheckBox("ETF/Dominance 오버레이 사용")
    self.chk_market_regime_use_etf_flow.setChecked(Config.DEFAULT_MARKET_REGIME_USE_ETF_FLOW)
    self.chk_market_regime_use_etf_flow.setToolTip(Config.TOOLTIPS.get("market_regime_use_etf_flow", ""))
    layout.addWidget(self.chk_market_regime_use_etf_flow, 2, 2, 1, 3)

    self.chk_fail_closed_on_stale_market_regime = QCheckBox("레짐 데이터 stale 시 신규 진입 차단")
    self.chk_fail_closed_on_stale_market_regime.setChecked(Config.DEFAULT_FAIL_CLOSED_ON_STALE_MARKET_REGIME)
    self.chk_fail_closed_on_stale_market_regime.setToolTip(Config.TOOLTIPS.get("fail_closed_on_stale_market_regime", ""))
    layout.addWidget(self.chk_fail_closed_on_stale_market_regime, 3, 0, 1, 4)

    group.setLayout(layout)
    return group
