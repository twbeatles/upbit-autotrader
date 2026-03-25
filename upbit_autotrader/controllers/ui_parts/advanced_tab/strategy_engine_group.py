from PyQt6.QtWidgets import QCheckBox, QComboBox, QGridLayout, QGroupBox, QLabel, QLineEdit, QDoubleSpinBox, QSpinBox

from upbit_autotrader.core.config import Config
from upbit_autotrader.strategies.catalog import STRATEGY_CATALOG, get_default_active_strategies, get_default_weights


def build_strategy_engine_group(self):
    group = QGroupBox("🧩 전략 엔진 (Single / Ensemble)")
    layout = QGridLayout()

    self.chk_use_strategy_engine = QCheckBox("전략 엔진 사용")
    self.chk_use_strategy_engine.setChecked(Config.DEFAULT_USE_STRATEGY_ENGINE)
    self.chk_use_strategy_engine.setToolTip(Config.TOOLTIPS.get("strategy_engine", ""))
    layout.addWidget(self.chk_use_strategy_engine, 0, 0, 1, 2)

    layout.addWidget(QLabel("실행 모드:"), 0, 2)
    self.combo_strategy_mode = QComboBox()
    self.combo_strategy_mode.addItem("단일 전략", "single")
    self.combo_strategy_mode.addItem("앙상블", "ensemble")
    default_mode_idx = self.combo_strategy_mode.findData(Config.DEFAULT_STRATEGY_MODE)
    if default_mode_idx >= 0:
        self.combo_strategy_mode.setCurrentIndex(default_mode_idx)
    layout.addWidget(self.combo_strategy_mode, 0, 3)

    layout.addWidget(QLabel("진입 게이트 정책:"), 0, 4)
    self.combo_engine_gate_policy = QComboBox()
    self.combo_engine_gate_policy.addItem("Legacy 우선", "legacy_first")
    self.combo_engine_gate_policy.addItem("엔진 전용", "engine_only")
    self.combo_engine_gate_policy.addItem("전략 인지형", "strategy_aware")
    gate_idx = self.combo_engine_gate_policy.findData(Config.DEFAULT_ENGINE_GATE_POLICY)
    if gate_idx >= 0:
        self.combo_engine_gate_policy.setCurrentIndex(gate_idx)
    self.combo_engine_gate_policy.setToolTip(Config.TOOLTIPS.get("engine_gate_policy", ""))
    layout.addWidget(self.combo_engine_gate_policy, 0, 5)

    layout.addWidget(QLabel("단일 전략:"), 1, 0)
    self.combo_single_strategy = QComboBox()
    for strategy_id, meta in STRATEGY_CATALOG.items():
        if not meta.get("tradeable") or meta.get("category") == "risk":
            continue
        self.combo_single_strategy.addItem(meta.get("name", strategy_id), strategy_id)
    idx_single = self.combo_single_strategy.findData(Config.DEFAULT_SINGLE_STRATEGY)
    if idx_single >= 0:
        self.combo_single_strategy.setCurrentIndex(idx_single)
    layout.addWidget(self.combo_single_strategy, 1, 1)

    layout.addWidget(QLabel("앙상블 임계점수:"), 1, 2)
    self.spin_ensemble_threshold = QSpinBox()
    self.spin_ensemble_threshold.setRange(0, 100)
    self.spin_ensemble_threshold.setValue(Config.DEFAULT_ENSEMBLE_THRESHOLD)
    self.spin_ensemble_threshold.setSuffix(" 점")
    layout.addWidget(self.spin_ensemble_threshold, 1, 3)

    layout.addWidget(QLabel("활성 전략 IDs:"), 2, 0)
    self.input_active_strategies = QLineEdit(",".join(get_default_active_strategies()))
    self.input_active_strategies.setPlaceholderText("예: volatility_breakout,ema_cross_trend")
    layout.addWidget(self.input_active_strategies, 2, 1, 1, 3)

    layout.addWidget(QLabel("가중치 (id:weight):"), 3, 0)
    default_weights_text = ",".join(f"{k}:{v}" for k, v in get_default_weights().items())
    self.input_strategy_weights = QLineEdit(default_weights_text)
    self.input_strategy_weights.setPlaceholderText("예: ema_cross_trend:1.2,rsi_reversion:0.8")
    layout.addWidget(self.input_strategy_weights, 3, 1, 1, 3)

    self.chk_use_volatility_targeting = QCheckBox("변동성 타게팅 사용")
    self.chk_use_volatility_targeting.setChecked(Config.DEFAULT_USE_VOLATILITY_TARGETING)
    layout.addWidget(self.chk_use_volatility_targeting, 4, 0, 1, 2)

    layout.addWidget(QLabel("목표 변동성(%):"), 4, 2)
    self.spin_target_vol = QDoubleSpinBox()
    self.spin_target_vol.setRange(0.5, 10.0)
    self.spin_target_vol.setSingleStep(0.1)
    self.spin_target_vol.setValue(Config.DEFAULT_TARGET_VOL_PCT)
    self.spin_target_vol.setSuffix(" %")
    layout.addWidget(self.spin_target_vol, 4, 3)

    self.chk_use_regime_filter = QCheckBox("레짐 필터 사용")
    self.chk_use_regime_filter.setChecked(Config.DEFAULT_USE_REGIME_FILTER)
    layout.addWidget(self.chk_use_regime_filter, 5, 0, 1, 2)

    layout.addWidget(QLabel("최소 ADX:"), 5, 2)
    self.spin_regime_min_adx = QDoubleSpinBox()
    self.spin_regime_min_adx.setRange(5.0, 60.0)
    self.spin_regime_min_adx.setSingleStep(1.0)
    self.spin_regime_min_adx.setValue(Config.DEFAULT_REGIME_MIN_ADX)
    layout.addWidget(self.spin_regime_min_adx, 5, 3)

    self.chk_use_drawdown_guard = QCheckBox("드로우다운 가드 사용")
    self.chk_use_drawdown_guard.setChecked(Config.DEFAULT_USE_DRAWDOWN_GUARD)
    layout.addWidget(self.chk_use_drawdown_guard, 6, 0, 1, 2)

    layout.addWidget(QLabel("최대 일손실(%):"), 6, 2)
    self.spin_drawdown_guard = QDoubleSpinBox()
    self.spin_drawdown_guard.setRange(1.0, 30.0)
    self.spin_drawdown_guard.setValue(Config.DEFAULT_DRAWDOWN_GUARD_PCT)
    self.spin_drawdown_guard.setSuffix(" %")
    layout.addWidget(self.spin_drawdown_guard, 6, 3)

    layout.addWidget(QLabel("최대 연속손실:"), 7, 0)
    self.spin_max_consecutive_losses = QSpinBox()
    self.spin_max_consecutive_losses.setRange(1, 10)
    self.spin_max_consecutive_losses.setValue(Config.DEFAULT_MAX_CONSECUTIVE_LOSSES)
    layout.addWidget(self.spin_max_consecutive_losses, 7, 1)

    group.setLayout(layout)
    return group
