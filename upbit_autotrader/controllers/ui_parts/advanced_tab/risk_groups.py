from PyQt6.QtWidgets import QCheckBox, QDoubleSpinBox, QGridLayout, QGroupBox, QLabel, QSpinBox

from upbit_autotrader.core.config import Config


def build_risk_group(self):
    group = QGroupBox("🛡️ 리스크 관리")
    layout = QGridLayout()

    self.chk_use_risk = QCheckBox("리스크 관리 사용")
    self.chk_use_risk.setChecked(Config.DEFAULT_USE_RISK_MGMT)
    layout.addWidget(self.chk_use_risk, 0, 0, 1, 2)

    layout.addWidget(QLabel("일일 최대 손실률:"), 1, 0)
    self.spin_max_loss = QDoubleSpinBox()
    self.spin_max_loss.setRange(1.0, 20.0)
    self.spin_max_loss.setValue(Config.DEFAULT_MAX_DAILY_LOSS)
    self.spin_max_loss.setSuffix(" %")
    layout.addWidget(self.spin_max_loss, 1, 1)

    layout.addWidget(QLabel("최대 보유 종목:"), 1, 2)
    self.spin_max_holdings = QSpinBox()
    self.spin_max_holdings.setRange(1, 20)
    self.spin_max_holdings.setValue(Config.DEFAULT_MAX_HOLDINGS)
    layout.addWidget(self.spin_max_holdings, 1, 3)

    self.chk_use_partial_tp = QCheckBox("분할 익절 사용 (3%→30%, 5%→30%, 8%→20%)")
    self.chk_use_partial_tp.setChecked(False)
    self.chk_use_partial_tp.setToolTip("수익률 단계별로 자동 분할 매도합니다")
    layout.addWidget(self.chk_use_partial_tp, 2, 0, 1, 4)

    self.chk_use_entry_scoring = QCheckBox("진입 점수 필터 사용")
    self.chk_use_entry_scoring.setChecked(False)
    self.chk_use_entry_scoring.setToolTip("가중치 기반 진입 점수가 임계값 이상일 때만 진입합니다.")
    layout.addWidget(self.chk_use_entry_scoring, 3, 0, 1, 2)

    layout.addWidget(QLabel("진입 임계 점수:"), 3, 2)
    self.spin_entry_score_threshold = QSpinBox()
    self.spin_entry_score_threshold.setRange(0, 100)
    self.spin_entry_score_threshold.setValue(Config.ENTRY_SCORE_THRESHOLD)
    self.spin_entry_score_threshold.setSuffix(" 점")
    layout.addWidget(self.spin_entry_score_threshold, 3, 3)

    self.chk_enable_account_wide_sync = QCheckBox("시작 시 계좌 전체 보유 동기화")
    self.chk_enable_account_wide_sync.setChecked(Config.DEFAULT_ENABLE_ACCOUNT_WIDE_SYNC)
    self.chk_enable_account_wide_sync.setToolTip(Config.TOOLTIPS.get("account_wide_sync", ""))
    layout.addWidget(self.chk_enable_account_wide_sync, 4, 0, 1, 2)

    self.chk_risk_include_unrealized = QCheckBox("리스크 계산에 미실현 손익 포함")
    self.chk_risk_include_unrealized.setChecked(Config.DEFAULT_RISK_INCLUDE_UNREALIZED)
    self.chk_risk_include_unrealized.setToolTip(Config.TOOLTIPS.get("risk_include_unrealized", ""))
    layout.addWidget(self.chk_risk_include_unrealized, 4, 2, 1, 2)

    self.chk_risk_include_external_holdings = QCheckBox("리스크 계산에 외부 보유 포함")
    self.chk_risk_include_external_holdings.setChecked(Config.DEFAULT_RISK_INCLUDE_EXTERNAL_HOLDINGS)
    self.chk_risk_include_external_holdings.setToolTip(Config.TOOLTIPS.get("risk_include_external_holdings", ""))
    layout.addWidget(self.chk_risk_include_external_holdings, 5, 0, 1, 2)

    self.chk_manual_review_on_timeout = QCheckBox("타임아웃 unresolved 시 수동검토 큐 적재")
    self.chk_manual_review_on_timeout.setChecked(Config.DEFAULT_MANUAL_REVIEW_ON_TIMEOUT)
    self.chk_manual_review_on_timeout.setToolTip(Config.TOOLTIPS.get("manual_review_on_timeout", ""))
    layout.addWidget(self.chk_manual_review_on_timeout, 5, 2, 1, 2)

    layout.addWidget(QLabel("가격피드 stale(초):"), 6, 0)
    self.spin_price_feed_stale_sec = QSpinBox()
    self.spin_price_feed_stale_sec.setRange(5, 120)
    self.spin_price_feed_stale_sec.setValue(int(Config.DEFAULT_PRICE_FEED_STALE_SEC))
    self.spin_price_feed_stale_sec.setToolTip(Config.TOOLTIPS.get("price_feed_stale_sec", ""))
    layout.addWidget(self.spin_price_feed_stale_sec, 6, 1)

    group.setLayout(layout)
    return group
