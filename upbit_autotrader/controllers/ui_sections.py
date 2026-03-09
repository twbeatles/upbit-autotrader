from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
)

from upbit_autotrader.core.config import Config
from upbit_autotrader.strategies.catalog import STRATEGY_CATALOG, get_default_active_strategies, get_default_weights


def build_ops_tab(self):
    """운영/수동검토 탭"""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(10)
    layout.setContentsMargins(15, 15, 15, 15)

    top_row = QHBoxLayout()
    self.lbl_manual_review_count = QLabel("🧾 수동검토 큐 0건")
    top_row.addWidget(self.lbl_manual_review_count)
    top_row.addStretch(1)

    self.btn_manual_review_refresh = QPushButton("🔄 새로고침")
    self.btn_manual_review_refresh.clicked.connect(self.refresh_manual_review_table)
    top_row.addWidget(self.btn_manual_review_refresh)

    self.btn_manual_review_requery = QPushButton("🔁 재조회")
    self.btn_manual_review_requery.clicked.connect(self.requery_selected_manual_review)
    top_row.addWidget(self.btn_manual_review_requery)

    self.btn_manual_review_resolve = QPushButton("✅ 해제")
    self.btn_manual_review_resolve.clicked.connect(self.resolve_selected_manual_review)
    top_row.addWidget(self.btn_manual_review_resolve)
    layout.addLayout(top_row)

    self.manual_review_table = QTableWidget()
    cols = ["queued_at", "age", "ticker", "uuid", "reason", "pending_state"]
    self.manual_review_table.setColumnCount(len(cols))
    self.manual_review_table.setHorizontalHeaderLabels(cols)
    header = self.manual_review_table.horizontalHeader()
    if header is not None:
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    self.manual_review_table.setAlternatingRowColors(True)
    self.manual_review_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    self.manual_review_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    vertical_header = self.manual_review_table.verticalHeader()
    if vertical_header is not None:
        vertical_header.setDefaultSectionSize(30)
    layout.addWidget(self.manual_review_table)

    if hasattr(self, "refresh_manual_review_table"):
        self.refresh_manual_review_table()
    return widget


def build_advanced_tab(self):
    """고급 설정 탭"""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(15)
    layout.setContentsMargins(15, 15, 15, 15)
    
    # RSI 필터
    group_rsi = QGroupBox("📈 RSI 필터")
    rsi_layout = QGridLayout()
    
    self.chk_use_rsi = QCheckBox("RSI 필터 사용")
    self.chk_use_rsi.setChecked(Config.DEFAULT_USE_RSI)
    rsi_layout.addWidget(self.chk_use_rsi, 0, 0, 1, 2)
    
    rsi_layout.addWidget(QLabel("RSI 상한선:"), 1, 0)
    self.spin_rsi_upper = QSpinBox()
    self.spin_rsi_upper.setRange(50, 90)
    self.spin_rsi_upper.setValue(Config.DEFAULT_RSI_UPPER)
    rsi_layout.addWidget(self.spin_rsi_upper, 1, 1)
    
    rsi_layout.addWidget(QLabel("RSI 기간:"), 1, 2)
    self.spin_rsi_period = QSpinBox()
    self.spin_rsi_period.setRange(5, 30)
    self.spin_rsi_period.setValue(Config.DEFAULT_RSI_PERIOD)
    rsi_layout.addWidget(self.spin_rsi_period, 1, 3)
    
    group_rsi.setLayout(rsi_layout)
    layout.addWidget(group_rsi)
    
    # MACD 필터
    group_macd = QGroupBox("📉 MACD 필터")
    macd_layout = QGridLayout()
    
    self.chk_use_macd = QCheckBox("MACD 필터 사용 (골든크로스 확인)")
    self.chk_use_macd.setChecked(Config.DEFAULT_USE_MACD)
    self.chk_use_macd.setToolTip("MACD가 Signal선 위에 있을 때만 매수합니다.\n상승 모멘텀을 확인하여 진입 정확도를 높입니다.")
    macd_layout.addWidget(self.chk_use_macd, 0, 0, 1, 2)
    
    group_macd.setLayout(macd_layout)
    layout.addWidget(group_macd)
    
    # 거래량 필터
    group_vol = QGroupBox("📊 거래량 필터")
    vol_layout = QGridLayout()
    
    self.chk_use_volume = QCheckBox("거래량 필터 사용")
    self.chk_use_volume.setChecked(Config.DEFAULT_USE_VOLUME)
    self.chk_use_volume.setToolTip("평균 거래량 대비 현재 거래량이 충분할 때만 매수합니다.\n거래량이 수반되지 않은 가격 상승은 신뢰도가 낮습니다.")
    vol_layout.addWidget(self.chk_use_volume, 0, 0, 1, 2)
    
    vol_layout.addWidget(QLabel("거래량 배수:"), 1, 0)
    self.spin_volume_mult = QDoubleSpinBox()
    self.spin_volume_mult.setRange(1.0, 5.0)
    self.spin_volume_mult.setSingleStep(0.1)
    self.spin_volume_mult.setValue(Config.DEFAULT_VOLUME_MULTIPLIER)
    self.spin_volume_mult.setToolTip("현재 거래량 >= 평균 거래량 × 배수 일 때 진입\n예: 1.5 = 평균의 1.5배 이상")
    vol_layout.addWidget(self.spin_volume_mult, 1, 1)
    
    group_vol.setLayout(vol_layout)
    layout.addWidget(group_vol)
    
    # 리스크 관리
    group_risk = QGroupBox("🛡️ 리스크 관리")
    risk_layout = QGridLayout()
    
    self.chk_use_risk = QCheckBox("리스크 관리 사용")
    self.chk_use_risk.setChecked(Config.DEFAULT_USE_RISK_MGMT)
    risk_layout.addWidget(self.chk_use_risk, 0, 0, 1, 2)
    
    risk_layout.addWidget(QLabel("일일 최대 손실률:"), 1, 0)
    self.spin_max_loss = QDoubleSpinBox()
    self.spin_max_loss.setRange(1.0, 20.0)
    self.spin_max_loss.setValue(Config.DEFAULT_MAX_DAILY_LOSS)
    self.spin_max_loss.setSuffix(" %")
    risk_layout.addWidget(self.spin_max_loss, 1, 1)
    
    risk_layout.addWidget(QLabel("최대 보유 종목:"), 1, 2)
    self.spin_max_holdings = QSpinBox()
    self.spin_max_holdings.setRange(1, 20)
    self.spin_max_holdings.setValue(Config.DEFAULT_MAX_HOLDINGS)
    risk_layout.addWidget(self.spin_max_holdings, 1, 3)
    
    # v2.7: 분할 익절 체크박스
    self.chk_use_partial_tp = QCheckBox("분할 익절 사용 (3%→30%, 5%→30%, 8%→20%)")
    self.chk_use_partial_tp.setChecked(False)
    self.chk_use_partial_tp.setToolTip("수익률 단계별로 자동 분할 매도합니다")
    risk_layout.addWidget(self.chk_use_partial_tp, 2, 0, 1, 4)

    # 진입 점수 필터
    self.chk_use_entry_scoring = QCheckBox("진입 점수 필터 사용")
    self.chk_use_entry_scoring.setChecked(False)
    self.chk_use_entry_scoring.setToolTip("가중치 기반 진입 점수가 임계값 이상일 때만 진입합니다.")
    risk_layout.addWidget(self.chk_use_entry_scoring, 3, 0, 1, 2)

    risk_layout.addWidget(QLabel("진입 임계 점수:"), 3, 2)
    self.spin_entry_score_threshold = QSpinBox()
    self.spin_entry_score_threshold.setRange(0, 100)
    self.spin_entry_score_threshold.setValue(Config.ENTRY_SCORE_THRESHOLD)
    self.spin_entry_score_threshold.setSuffix(" 점")
    risk_layout.addWidget(self.spin_entry_score_threshold, 3, 3)

    self.chk_enable_account_wide_sync = QCheckBox("시작 시 계좌 전체 보유 동기화")
    self.chk_enable_account_wide_sync.setChecked(Config.DEFAULT_ENABLE_ACCOUNT_WIDE_SYNC)
    self.chk_enable_account_wide_sync.setToolTip(Config.TOOLTIPS.get("account_wide_sync", ""))
    risk_layout.addWidget(self.chk_enable_account_wide_sync, 4, 0, 1, 2)

    self.chk_risk_include_unrealized = QCheckBox("리스크 계산에 미실현 손익 포함")
    self.chk_risk_include_unrealized.setChecked(Config.DEFAULT_RISK_INCLUDE_UNREALIZED)
    self.chk_risk_include_unrealized.setToolTip(Config.TOOLTIPS.get("risk_include_unrealized", ""))
    risk_layout.addWidget(self.chk_risk_include_unrealized, 4, 2, 1, 2)

    self.chk_risk_include_external_holdings = QCheckBox("리스크 계산에 외부 보유 포함")
    self.chk_risk_include_external_holdings.setChecked(Config.DEFAULT_RISK_INCLUDE_EXTERNAL_HOLDINGS)
    self.chk_risk_include_external_holdings.setToolTip(Config.TOOLTIPS.get("risk_include_external_holdings", ""))
    risk_layout.addWidget(self.chk_risk_include_external_holdings, 5, 0, 1, 2)

    self.chk_manual_review_on_timeout = QCheckBox("타임아웃 unresolved 시 수동검토 큐 적재")
    self.chk_manual_review_on_timeout.setChecked(Config.DEFAULT_MANUAL_REVIEW_ON_TIMEOUT)
    self.chk_manual_review_on_timeout.setToolTip(Config.TOOLTIPS.get("manual_review_on_timeout", ""))
    risk_layout.addWidget(self.chk_manual_review_on_timeout, 5, 2, 1, 2)

    risk_layout.addWidget(QLabel("가격피드 stale(초):"), 6, 0)
    self.spin_price_feed_stale_sec = QSpinBox()
    self.spin_price_feed_stale_sec.setRange(5, 120)
    self.spin_price_feed_stale_sec.setValue(int(Config.DEFAULT_PRICE_FEED_STALE_SEC))
    self.spin_price_feed_stale_sec.setToolTip(Config.TOOLTIPS.get("price_feed_stale_sec", ""))
    risk_layout.addWidget(self.spin_price_feed_stale_sec, 6, 1)
    
    group_risk.setLayout(risk_layout)
    layout.addWidget(group_risk)

    # 전략 엔진 설정 (v3.2)
    group_strategy_engine = QGroupBox("🧩 전략 엔진 (Single / Ensemble)")
    se_layout = QGridLayout()

    self.chk_use_strategy_engine = QCheckBox("전략 엔진 사용")
    self.chk_use_strategy_engine.setChecked(Config.DEFAULT_USE_STRATEGY_ENGINE)
    self.chk_use_strategy_engine.setToolTip(Config.TOOLTIPS.get("strategy_engine", ""))
    se_layout.addWidget(self.chk_use_strategy_engine, 0, 0, 1, 2)

    se_layout.addWidget(QLabel("실행 모드:"), 0, 2)
    self.combo_strategy_mode = QComboBox()
    self.combo_strategy_mode.addItem("단일 전략", "single")
    self.combo_strategy_mode.addItem("앙상블", "ensemble")
    default_mode_idx = self.combo_strategy_mode.findData(Config.DEFAULT_STRATEGY_MODE)
    if default_mode_idx >= 0:
        self.combo_strategy_mode.setCurrentIndex(default_mode_idx)
    se_layout.addWidget(self.combo_strategy_mode, 0, 3)

    se_layout.addWidget(QLabel("진입 게이트 정책:"), 0, 4)
    self.combo_engine_gate_policy = QComboBox()
    self.combo_engine_gate_policy.addItem("Legacy 우선", "legacy_first")
    self.combo_engine_gate_policy.addItem("엔진 전용", "engine_only")
    self.combo_engine_gate_policy.addItem("전략 인지형", "strategy_aware")
    gate_idx = self.combo_engine_gate_policy.findData(Config.DEFAULT_ENGINE_GATE_POLICY)
    if gate_idx >= 0:
        self.combo_engine_gate_policy.setCurrentIndex(gate_idx)
    self.combo_engine_gate_policy.setToolTip(Config.TOOLTIPS.get("engine_gate_policy", ""))
    se_layout.addWidget(self.combo_engine_gate_policy, 0, 5)

    se_layout.addWidget(QLabel("단일 전략:"), 1, 0)
    self.combo_single_strategy = QComboBox()
    for strategy_id, meta in STRATEGY_CATALOG.items():
        if not meta.get("tradeable"):
            continue
        if meta.get("category") == "risk":
            continue
        self.combo_single_strategy.addItem(meta.get("name", strategy_id), strategy_id)
    idx_single = self.combo_single_strategy.findData(Config.DEFAULT_SINGLE_STRATEGY)
    if idx_single >= 0:
        self.combo_single_strategy.setCurrentIndex(idx_single)
    se_layout.addWidget(self.combo_single_strategy, 1, 1)

    se_layout.addWidget(QLabel("앙상블 임계점수:"), 1, 2)
    self.spin_ensemble_threshold = QSpinBox()
    self.spin_ensemble_threshold.setRange(0, 100)
    self.spin_ensemble_threshold.setValue(Config.DEFAULT_ENSEMBLE_THRESHOLD)
    self.spin_ensemble_threshold.setSuffix(" 점")
    se_layout.addWidget(self.spin_ensemble_threshold, 1, 3)

    se_layout.addWidget(QLabel("활성 전략 IDs:"), 2, 0)
    self.input_active_strategies = QLineEdit(",".join(get_default_active_strategies()))
    self.input_active_strategies.setPlaceholderText("예: volatility_breakout,ema_cross_trend")
    se_layout.addWidget(self.input_active_strategies, 2, 1, 1, 3)

    se_layout.addWidget(QLabel("가중치 (id:weight):"), 3, 0)
    default_weights_text = ",".join(f"{k}:{v}" for k, v in get_default_weights().items())
    self.input_strategy_weights = QLineEdit(default_weights_text)
    self.input_strategy_weights.setPlaceholderText("예: ema_cross_trend:1.2,rsi_reversion:0.8")
    se_layout.addWidget(self.input_strategy_weights, 3, 1, 1, 3)

    self.chk_use_volatility_targeting = QCheckBox("변동성 타게팅 사용")
    self.chk_use_volatility_targeting.setChecked(Config.DEFAULT_USE_VOLATILITY_TARGETING)
    se_layout.addWidget(self.chk_use_volatility_targeting, 4, 0, 1, 2)

    se_layout.addWidget(QLabel("목표 변동성(%):"), 4, 2)
    self.spin_target_vol = QDoubleSpinBox()
    self.spin_target_vol.setRange(0.5, 10.0)
    self.spin_target_vol.setSingleStep(0.1)
    self.spin_target_vol.setValue(Config.DEFAULT_TARGET_VOL_PCT)
    self.spin_target_vol.setSuffix(" %")
    se_layout.addWidget(self.spin_target_vol, 4, 3)

    self.chk_use_regime_filter = QCheckBox("레짐 필터 사용")
    self.chk_use_regime_filter.setChecked(Config.DEFAULT_USE_REGIME_FILTER)
    se_layout.addWidget(self.chk_use_regime_filter, 5, 0, 1, 2)

    se_layout.addWidget(QLabel("최소 ADX:"), 5, 2)
    self.spin_regime_min_adx = QDoubleSpinBox()
    self.spin_regime_min_adx.setRange(5.0, 60.0)
    self.spin_regime_min_adx.setSingleStep(1.0)
    self.spin_regime_min_adx.setValue(Config.DEFAULT_REGIME_MIN_ADX)
    se_layout.addWidget(self.spin_regime_min_adx, 5, 3)

    self.chk_use_drawdown_guard = QCheckBox("드로우다운 가드 사용")
    self.chk_use_drawdown_guard.setChecked(Config.DEFAULT_USE_DRAWDOWN_GUARD)
    se_layout.addWidget(self.chk_use_drawdown_guard, 6, 0, 1, 2)

    se_layout.addWidget(QLabel("최대 일손실(%):"), 6, 2)
    self.spin_drawdown_guard = QDoubleSpinBox()
    self.spin_drawdown_guard.setRange(1.0, 30.0)
    self.spin_drawdown_guard.setValue(Config.DEFAULT_DRAWDOWN_GUARD_PCT)
    self.spin_drawdown_guard.setSuffix(" %")
    se_layout.addWidget(self.spin_drawdown_guard, 6, 3)

    se_layout.addWidget(QLabel("최대 연속손실:"), 7, 0)
    self.spin_max_consecutive_losses = QSpinBox()
    self.spin_max_consecutive_losses.setRange(1, 10)
    self.spin_max_consecutive_losses.setValue(Config.DEFAULT_MAX_CONSECUTIVE_LOSSES)
    se_layout.addWidget(self.spin_max_consecutive_losses, 7, 1)

    group_strategy_engine.setLayout(se_layout)
    layout.addWidget(group_strategy_engine)

    # 페이퍼 트레이딩 설정 (v3.2)
    group_paper = QGroupBox("🧪 페이퍼 트레이딩")
    paper_layout = QGridLayout()
    self.chk_paper_trading = QCheckBox("페이퍼 트레이딩 사용")
    self.chk_paper_trading.setChecked(Config.DEFAULT_PAPER_TRADING)
    self.chk_paper_trading.setToolTip(Config.TOOLTIPS.get("paper_trading", ""))
    paper_layout.addWidget(self.chk_paper_trading, 0, 0, 1, 2)
    self.chk_paper_trading.toggled.connect(lambda _checked: self.refresh_trade_action_buttons())

    self.chk_paper_allow_without_login = QCheckBox("무로그인 시작 허용")
    self.chk_paper_allow_without_login.setChecked(Config.DEFAULT_PAPER_ALLOW_WITHOUT_LOGIN)
    self.chk_paper_allow_without_login.setToolTip(Config.TOOLTIPS.get("paper_allow_without_login", ""))
    paper_layout.addWidget(self.chk_paper_allow_without_login, 0, 2, 1, 2)
    self.chk_paper_allow_without_login.toggled.connect(lambda _checked: self.refresh_trade_action_buttons())

    paper_layout.addWidget(QLabel("수수료(bps):"), 1, 0)
    self.spin_paper_fee_bps = QDoubleSpinBox()
    self.spin_paper_fee_bps.setRange(0.0, 100.0)
    self.spin_paper_fee_bps.setSingleStep(0.5)
    self.spin_paper_fee_bps.setValue(Config.DEFAULT_PAPER_FEE_BPS)
    paper_layout.addWidget(self.spin_paper_fee_bps, 1, 1)

    paper_layout.addWidget(QLabel("슬리피지(bps):"), 1, 2)
    self.spin_paper_slippage_bps = QDoubleSpinBox()
    self.spin_paper_slippage_bps.setRange(0.0, 200.0)
    self.spin_paper_slippage_bps.setSingleStep(0.5)
    self.spin_paper_slippage_bps.setValue(Config.DEFAULT_PAPER_SLIPPAGE_BPS)
    paper_layout.addWidget(self.spin_paper_slippage_bps, 1, 3)

    paper_layout.addWidget(QLabel("초기 시드(KRW):"), 2, 0)
    self.spin_paper_seed_krw = QDoubleSpinBox()
    self.spin_paper_seed_krw.setRange(100000.0, 1000000000.0)
    self.spin_paper_seed_krw.setSingleStep(100000.0)
    self.spin_paper_seed_krw.setDecimals(0)
    self.spin_paper_seed_krw.setValue(float(Config.DEFAULT_PAPER_SEED_KRW))
    self.spin_paper_seed_krw.setToolTip(Config.TOOLTIPS.get("paper_seed_krw", ""))
    paper_layout.addWidget(self.spin_paper_seed_krw, 2, 1)
    group_paper.setLayout(paper_layout)
    layout.addWidget(group_paper)

    # 확장 리스크/사이징 설정 (v3.3)
    group_ext_risk = QGroupBox("📐 확장 리스크/사이징")
    ext_risk_layout = QGridLayout()

    self.chk_use_risk_budget_sizing = QCheckBox("리스크 예산 기반 사이징 사용")
    self.chk_use_risk_budget_sizing.setChecked(Config.DEFAULT_USE_RISK_BUDGET_SIZING)
    self.chk_use_risk_budget_sizing.setToolTip(Config.TOOLTIPS.get("risk_budget_sizing", ""))
    ext_risk_layout.addWidget(self.chk_use_risk_budget_sizing, 0, 0, 1, 2)

    ext_risk_layout.addWidget(QLabel("리스크 예산(%):"), 0, 2)
    self.spin_risk_budget_pct = QDoubleSpinBox()
    self.spin_risk_budget_pct.setRange(0.1, 5.0)
    self.spin_risk_budget_pct.setSingleStep(0.1)
    self.spin_risk_budget_pct.setValue(Config.DEFAULT_RISK_BUDGET_PCT)
    self.spin_risk_budget_pct.setSuffix(" %")
    self.spin_risk_budget_pct.setToolTip(Config.TOOLTIPS.get("risk_budget_pct", ""))
    ext_risk_layout.addWidget(self.spin_risk_budget_pct, 0, 3)

    ext_risk_layout.addWidget(QLabel("ATR 손절 배수:"), 1, 0)
    self.spin_atr_stop_mult = QDoubleSpinBox()
    self.spin_atr_stop_mult.setRange(0.5, 10.0)
    self.spin_atr_stop_mult.setSingleStep(0.1)
    self.spin_atr_stop_mult.setValue(Config.DEFAULT_ATR_STOP_MULT)
    self.spin_atr_stop_mult.setToolTip(Config.TOOLTIPS.get("atr_stop_mult", ""))
    ext_risk_layout.addWidget(self.spin_atr_stop_mult, 1, 1)

    ext_risk_layout.addWidget(QLabel("최소 손절(%):"), 1, 2)
    self.spin_min_stop_pct = QDoubleSpinBox()
    self.spin_min_stop_pct.setRange(0.1, 5.0)
    self.spin_min_stop_pct.setSingleStep(0.1)
    self.spin_min_stop_pct.setValue(Config.DEFAULT_MIN_STOP_PCT)
    self.spin_min_stop_pct.setSuffix(" %")
    self.spin_min_stop_pct.setToolTip(Config.TOOLTIPS.get("min_stop_pct", ""))
    ext_risk_layout.addWidget(self.spin_min_stop_pct, 1, 3)

    ext_risk_layout.addWidget(QLabel("최대 비중(%):"), 1, 4)
    self.spin_max_betting_pct = QDoubleSpinBox()
    self.spin_max_betting_pct.setRange(1.0, 100.0)
    self.spin_max_betting_pct.setSingleStep(1.0)
    self.spin_max_betting_pct.setValue(Config.DEFAULT_MAX_BETTING_PCT)
    self.spin_max_betting_pct.setSuffix(" %")
    self.spin_max_betting_pct.setToolTip(Config.TOOLTIPS.get("max_betting_pct", ""))
    ext_risk_layout.addWidget(self.spin_max_betting_pct, 1, 5)

    self.chk_use_kelly_adjustment = QCheckBox("Kelly 보정 사용")
    self.chk_use_kelly_adjustment.setChecked(Config.DEFAULT_USE_KELLY_ADJUSTMENT)
    self.chk_use_kelly_adjustment.setToolTip(Config.TOOLTIPS.get("kelly_adjustment", ""))
    ext_risk_layout.addWidget(self.chk_use_kelly_adjustment, 2, 0, 1, 2)

    ext_risk_layout.addWidget(QLabel("Kelly 스케일:"), 2, 2)
    self.spin_kelly_scale = QDoubleSpinBox()
    self.spin_kelly_scale.setRange(0.05, 1.0)
    self.spin_kelly_scale.setSingleStep(0.05)
    self.spin_kelly_scale.setValue(Config.DEFAULT_KELLY_SCALE)
    ext_risk_layout.addWidget(self.spin_kelly_scale, 2, 3)

    self.chk_drawdown_state_enabled = QCheckBox("드로우다운 상태머신 사용")
    self.chk_drawdown_state_enabled.setChecked(Config.DEFAULT_DRAWDOWN_STATE_ENABLED)
    self.chk_drawdown_state_enabled.setToolTip(Config.TOOLTIPS.get("drawdown_state", ""))
    ext_risk_layout.addWidget(self.chk_drawdown_state_enabled, 3, 0, 1, 2)

    ext_risk_layout.addWidget(QLabel("주의/방어/중단(%):"), 3, 2)
    dd_row = QHBoxLayout()
    self.spin_dd_caution_pct = QDoubleSpinBox()
    self.spin_dd_caution_pct.setRange(1.0, 30.0)
    self.spin_dd_caution_pct.setValue(Config.DEFAULT_DD_CAUTION_PCT)
    self.spin_dd_caution_pct.setSuffix("%")
    dd_row.addWidget(self.spin_dd_caution_pct)
    self.spin_dd_defense_pct = QDoubleSpinBox()
    self.spin_dd_defense_pct.setRange(1.0, 30.0)
    self.spin_dd_defense_pct.setValue(Config.DEFAULT_DD_DEFENSE_PCT)
    self.spin_dd_defense_pct.setSuffix("%")
    dd_row.addWidget(self.spin_dd_defense_pct)
    self.spin_dd_halt_pct = QDoubleSpinBox()
    self.spin_dd_halt_pct.setRange(1.0, 50.0)
    self.spin_dd_halt_pct.setValue(Config.DEFAULT_DD_HALT_PCT)
    self.spin_dd_halt_pct.setSuffix("%")
    dd_row.addWidget(self.spin_dd_halt_pct)
    ext_risk_layout.addLayout(dd_row, 3, 3, 1, 3)

    ext_risk_layout.addWidget(QLabel("상관창(캔들):"), 4, 0)
    self.spin_portfolio_corr_window = QSpinBox()
    self.spin_portfolio_corr_window.setRange(20, 300)
    self.spin_portfolio_corr_window.setValue(Config.DEFAULT_PORTFOLIO_CORR_WINDOW)
    self.spin_portfolio_corr_window.setToolTip(Config.TOOLTIPS.get("portfolio_corr_window", ""))
    ext_risk_layout.addWidget(self.spin_portfolio_corr_window, 4, 1)

    ext_risk_layout.addWidget(QLabel("상관 익스포저 한도(%):"), 4, 2)
    self.spin_max_correlation_exposure_pct = QDoubleSpinBox()
    self.spin_max_correlation_exposure_pct.setRange(10.0, 100.0)
    self.spin_max_correlation_exposure_pct.setSingleStep(5.0)
    self.spin_max_correlation_exposure_pct.setValue(Config.DEFAULT_MAX_CORRELATION_EXPOSURE_PCT)
    self.spin_max_correlation_exposure_pct.setSuffix(" %")
    self.spin_max_correlation_exposure_pct.setToolTip(Config.TOOLTIPS.get("max_correlation_exposure_pct", ""))
    ext_risk_layout.addWidget(self.spin_max_correlation_exposure_pct, 4, 3)

    self.chk_persist_reconciliation_state = QCheckBox("주문 복구 상태 영속화")
    self.chk_persist_reconciliation_state.setChecked(Config.DEFAULT_PERSIST_RECONCILIATION_STATE)
    self.chk_persist_reconciliation_state.setToolTip(Config.TOOLTIPS.get("persist_reconciliation", ""))
    ext_risk_layout.addWidget(self.chk_persist_reconciliation_state, 4, 4, 1, 2)

    group_ext_risk.setLayout(ext_risk_layout)
    layout.addWidget(group_ext_risk)

    # 실행 모델 설정 (v3.3)
    group_exec = QGroupBox("⚙️ 실행 모델 / TWAP")
    exec_layout = QGridLayout()

    self.chk_use_execution_model = QCheckBox("실행 모델 사용")
    self.chk_use_execution_model.setChecked(Config.DEFAULT_USE_EXECUTION_MODEL)
    self.chk_use_execution_model.setToolTip(Config.TOOLTIPS.get("execution_model", ""))
    exec_layout.addWidget(self.chk_use_execution_model, 0, 0, 1, 2)

    exec_layout.addWidget(QLabel("실행 모드:"), 0, 2)
    self.combo_execution_mode = QComboBox()
    self.combo_execution_mode.addItem("일반 시장가", "single_market")
    self.combo_execution_mode.addItem("TWAP 분할", "twap_market")
    idx_exec = self.combo_execution_mode.findData(Config.DEFAULT_EXECUTION_MODE)
    if idx_exec >= 0:
        self.combo_execution_mode.setCurrentIndex(idx_exec)
    exec_layout.addWidget(self.combo_execution_mode, 0, 3)

    exec_layout.addWidget(QLabel("슬리피지 가드(bps):"), 1, 0)
    self.spin_expected_slippage_guard_bps = QDoubleSpinBox()
    self.spin_expected_slippage_guard_bps.setRange(1.0, 300.0)
    self.spin_expected_slippage_guard_bps.setSingleStep(1.0)
    self.spin_expected_slippage_guard_bps.setValue(Config.DEFAULT_EXPECTED_SLIPPAGE_GUARD_BPS)
    self.spin_expected_slippage_guard_bps.setToolTip(Config.TOOLTIPS.get("expected_slippage_guard_bps", ""))
    exec_layout.addWidget(self.spin_expected_slippage_guard_bps, 1, 1)

    exec_layout.addWidget(QLabel("TWAP 분할 수:"), 1, 2)
    self.spin_twap_slices = QSpinBox()
    self.spin_twap_slices.setRange(2, 20)
    self.spin_twap_slices.setValue(Config.DEFAULT_TWAP_SLICES)
    exec_layout.addWidget(self.spin_twap_slices, 1, 3)

    exec_layout.addWidget(QLabel("TWAP 간격(초):"), 1, 4)
    self.spin_twap_interval_sec = QSpinBox()
    self.spin_twap_interval_sec.setRange(1, 120)
    self.spin_twap_interval_sec.setValue(Config.DEFAULT_TWAP_INTERVAL_SEC)
    exec_layout.addWidget(self.spin_twap_interval_sec, 1, 5)

    group_exec.setLayout(exec_layout)
    layout.addWidget(group_exec)

    # 메타 시그널 설정 (v3.3)
    group_meta = QGroupBox("🧠 메타 시그널 / 가중치 리밸런싱")
    meta_layout = QGridLayout()

    self.chk_use_meta_signal = QCheckBox("메타 시그널 게이트 사용")
    self.chk_use_meta_signal.setChecked(Config.DEFAULT_USE_META_SIGNAL)
    self.chk_use_meta_signal.setToolTip(Config.TOOLTIPS.get("meta_signal", ""))
    meta_layout.addWidget(self.chk_use_meta_signal, 0, 0, 1, 2)

    meta_layout.addWidget(QLabel("최소 기대값(%):"), 0, 2)
    self.spin_meta_min_expectancy = QDoubleSpinBox()
    self.spin_meta_min_expectancy.setRange(-10.0, 20.0)
    self.spin_meta_min_expectancy.setSingleStep(0.1)
    self.spin_meta_min_expectancy.setValue(Config.DEFAULT_META_MIN_EXPECTANCY)
    self.spin_meta_min_expectancy.setToolTip(Config.TOOLTIPS.get("meta_min_expectancy", ""))
    meta_layout.addWidget(self.spin_meta_min_expectancy, 0, 3)

    meta_layout.addWidget(QLabel("메타 점수 임계:"), 0, 4)
    self.spin_meta_score_threshold = QSpinBox()
    self.spin_meta_score_threshold.setRange(0, 100)
    self.spin_meta_score_threshold.setValue(int(Config.DEFAULT_META_SCORE_THRESHOLD))
    self.spin_meta_score_threshold.setToolTip(Config.TOOLTIPS.get("meta_score_threshold", ""))
    meta_layout.addWidget(self.spin_meta_score_threshold, 0, 5)

    self.chk_weight_rebalance_daily = QCheckBox("전략 가중치 일일 리밸런싱")
    self.chk_weight_rebalance_daily.setChecked(Config.DEFAULT_WEIGHT_REBALANCE_DAILY)
    self.chk_weight_rebalance_daily.setToolTip(Config.TOOLTIPS.get("weight_rebalance_daily", ""))
    meta_layout.addWidget(self.chk_weight_rebalance_daily, 1, 0, 1, 2)

    meta_layout.addWidget(QLabel("가중치 최소/최대:"), 1, 2)
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
    meta_layout.addLayout(w_row, 1, 3, 1, 3)

    group_meta.setLayout(meta_layout)
    layout.addWidget(group_meta)

    # 알림 채널 설정 (v3.3)
    group_alert = QGroupBox("🔔 운영 알림 채널")
    alert_layout = QGridLayout()
    self.chk_enable_discord_alerts = QCheckBox("Discord 알림 사용")
    self.chk_enable_discord_alerts.setChecked(Config.DEFAULT_ENABLE_DISCORD_ALERTS)
    self.chk_enable_discord_alerts.setToolTip(Config.TOOLTIPS.get("discord_alerts", ""))
    alert_layout.addWidget(self.chk_enable_discord_alerts, 0, 0, 1, 2)

    alert_layout.addWidget(QLabel("Discord Webhook:"), 1, 0)
    self.input_discord_webhook = QLineEdit(Config.DEFAULT_DISCORD_WEBHOOK)
    self.input_discord_webhook.setPlaceholderText("https://discord.com/api/webhooks/...")
    alert_layout.addWidget(self.input_discord_webhook, 1, 1, 1, 5)
    group_alert.setLayout(alert_layout)
    layout.addWidget(group_alert)
    
    # v3.0: 고급 리스크 관리
    # In the refactored facade, availability is determined by whether the strategy manager is loaded.
    if getattr(self, "strategy", None) is not None:
        group_adv_risk = QGroupBox("🚀 고급 리스크 관리 (v3.0)")
        adv_risk_layout = QGridLayout()
        
        # 재진입 쿨다운
        self.chk_use_cooldown = QCheckBox("재진입 쿨다운 사용")
        self.chk_use_cooldown.setToolTip("매도 후 일정 시간 동안 동일 코인 재매수 방지\n휩쏘에 휘둘리지 않도록 보호")
        adv_risk_layout.addWidget(self.chk_use_cooldown, 0, 0)
        
        adv_risk_layout.addWidget(QLabel("쿨다운 시간:"), 0, 1)
        self.spin_cooldown = QSpinBox()
        self.spin_cooldown.setRange(5, 120)
        self.spin_cooldown.setValue(30)
        self.spin_cooldown.setSuffix(" 분")
        adv_risk_layout.addWidget(self.spin_cooldown, 0, 2)
        
        # 시간 기반 청산
        self.chk_use_time_exit = QCheckBox("시간 기반 청산")
        self.chk_use_time_exit.setToolTip("일정 시간 경과 시 자동 청산")
        adv_risk_layout.addWidget(self.chk_use_time_exit, 1, 0)
        
        adv_risk_layout.addWidget(QLabel("최대 보유:"), 1, 1)
        self.spin_max_holding_hours = QSpinBox()
        self.spin_max_holding_hours.setRange(1, 72)
        self.spin_max_holding_hours.setValue(24)
        self.spin_max_holding_hours.setSuffix(" 시간")
        adv_risk_layout.addWidget(self.spin_max_holding_hours, 1, 2)
        
        # 동적 포지션 사이징
        self.chk_use_dynamic_position = QCheckBox("동적 포지션 사이징 (Anti-Martingale)")
        self.chk_use_dynamic_position.setToolTip("연속 이익 시 투자비중 확대, 연속 손실 시 축소")
        adv_risk_layout.addWidget(self.chk_use_dynamic_position, 2, 0, 1, 3)
        
        group_adv_risk.setLayout(adv_risk_layout)
        layout.addWidget(group_adv_risk)
        
        # v3.0: 고급 알고리즘
        group_adv_algo = QGroupBox("🧠 고급 알고리즘 (v3.0)")
        adv_algo_layout = QGridLayout()
        
        # MTF
        self.chk_use_mtf = QCheckBox("다중 시간프레임(MTF) 분석")
        self.chk_use_mtf.setToolTip("일봉과 단기봉 추세 일치 시에만 매수")
        adv_algo_layout.addWidget(self.chk_use_mtf, 0, 0)
        
        # 갭 분석
        self.chk_use_gap = QCheckBox("갭 분석 및 K값 자동 조정")
        self.chk_use_gap.setToolTip("갭업 시 K값 축소(신중), 갭다운 시 K값 확대(적극)")
        adv_algo_layout.addWidget(self.chk_use_gap, 0, 1)
        
        # 돌파 확인
        self.chk_use_breakout_confirm = QCheckBox("돌파 확인 (N틱 유지)")
        self.chk_use_breakout_confirm.setToolTip("목표가 돌파 후 일정 틱 동안 유지되어야 매수")
        adv_algo_layout.addWidget(self.chk_use_breakout_confirm, 1, 0)
        
        adv_algo_layout.addWidget(QLabel("확인 틱수:"), 1, 1)
        self.spin_breakout_ticks = QSpinBox()
        self.spin_breakout_ticks.setRange(1, 10)
        self.spin_breakout_ticks.setValue(3)
        adv_algo_layout.addWidget(self.spin_breakout_ticks, 1, 2)
        
        group_adv_algo.setLayout(adv_algo_layout)
        layout.addWidget(group_adv_algo)
        
        # 긴급 청산 버튼
        group_emergency = QGroupBox("🚨 긴급 조치")
        emergency_layout = QHBoxLayout()
        
        self.btn_emergency_close = QPushButton("🚨 전량 긴급 청산")
        self.btn_emergency_close.setStyleSheet("""
            QPushButton {
                background-color: #e63946;
                font-weight: bold;
                font-size: 14px;
                padding: 15px 30px;
            }
            QPushButton:hover {
                background-color: #d62839;
            }
        """)
        self.btn_emergency_close.clicked.connect(self.show_emergency_dialog)
        self.btn_emergency_close.setToolTip("모든 보유 코인을 시장가로 즉시 매도합니다")
        emergency_layout.addWidget(self.btn_emergency_close)
        emergency_layout.addStretch(1)
        
        group_emergency.setLayout(emergency_layout)
        layout.addWidget(group_emergency)
    
    # 프리셋
    group_preset = QGroupBox("📋 전략 프리셋")
    preset_layout = QVBoxLayout()
    
    # 프리셋 버튼 행
    btn_row = QHBoxLayout()
    
    btn_aggressive = QPushButton("🔥 공격적")
    btn_aggressive.setToolTip(Config.DEFAULT_PRESETS['aggressive']['description'])
    btn_aggressive.clicked.connect(lambda: self.apply_preset("aggressive"))
    
    btn_normal = QPushButton("⚖️ 표준")
    btn_normal.setToolTip(Config.DEFAULT_PRESETS['normal']['description'])
    btn_normal.clicked.connect(lambda: self.apply_preset("normal"))
    
    btn_conservative = QPushButton("🛡️ 보수적")
    btn_conservative.setToolTip(Config.DEFAULT_PRESETS['conservative']['description'])
    btn_conservative.clicked.connect(lambda: self.apply_preset("conservative"))
    
    btn_row.addWidget(btn_aggressive)
    btn_row.addWidget(btn_normal)
    btn_row.addWidget(btn_conservative)
    preset_layout.addLayout(btn_row)
    
    # 현재 프리셋 상태 및 관리 버튼
    manage_row = QHBoxLayout()
    
    self.lbl_current_preset = QLabel("💡 프리셋을 선택하거나 직접 값을 조정하세요")
    self.lbl_current_preset.setStyleSheet("color: #90e0ef; font-style: italic;")
    manage_row.addWidget(self.lbl_current_preset)
    
    manage_row.addStretch(1)
    
    btn_manage_presets = QPushButton("📁 프리셋 관리")
    btn_manage_presets.clicked.connect(self.open_preset_manager)
    manage_row.addWidget(btn_manage_presets)
    
    preset_layout.addLayout(manage_row)
    
    group_preset.setLayout(preset_layout)
    layout.addWidget(group_preset)
    
    layout.addStretch(1)
    return widget
