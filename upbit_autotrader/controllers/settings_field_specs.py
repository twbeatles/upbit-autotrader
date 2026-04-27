from dataclasses import dataclass
from typing import Any, Callable, Iterable


@dataclass(frozen=True)
class FieldSpec:
    key: str
    attr: str
    kind: str
    default: Callable[[Any], Any]


def _cfg(name: str) -> Callable[[Any], Any]:
    return lambda config: getattr(config, name)


def _const(value: Any) -> Callable[[Any], Any]:
    return lambda _config: value


COMMON_FIELD_SPECS: tuple[FieldSpec, ...] = (
    FieldSpec("coins", "input_coins", "text", _cfg("DEFAULT_COINS")),
    FieldSpec("candle", "combo_candle", "combo_text", _cfg("DEFAULT_CANDLE")),
    FieldSpec("betting_ratio", "spin_betting", "spin", _cfg("DEFAULT_BETTING_RATIO")),
    FieldSpec("k_value", "spin_k", "spin", _cfg("DEFAULT_K_VALUE")),
    FieldSpec("ts_start", "spin_ts_start", "spin", _cfg("DEFAULT_TS_START")),
    FieldSpec("ts_stop", "spin_ts_stop", "spin", _cfg("DEFAULT_TS_STOP")),
    FieldSpec("loss_cut", "spin_loss", "spin", _cfg("DEFAULT_LOSS_CUT")),
    FieldSpec("use_rsi", "chk_use_rsi", "check", _cfg("DEFAULT_USE_RSI")),
    FieldSpec("rsi_upper", "spin_rsi_upper", "spin", _cfg("DEFAULT_RSI_UPPER")),
    FieldSpec("rsi_period", "spin_rsi_period", "spin", _cfg("DEFAULT_RSI_PERIOD")),
    FieldSpec("use_volume", "chk_use_volume", "check", _cfg("DEFAULT_USE_VOLUME")),
    FieldSpec("volume_mult", "spin_volume_mult", "spin", _cfg("DEFAULT_VOLUME_MULTIPLIER")),
    FieldSpec("use_risk", "chk_use_risk", "check", _cfg("DEFAULT_USE_RISK_MGMT")),
    FieldSpec("max_daily_loss", "spin_max_loss", "spin", _cfg("DEFAULT_MAX_DAILY_LOSS")),
    FieldSpec("max_holdings", "spin_max_holdings", "spin", _cfg("DEFAULT_MAX_HOLDINGS")),
    FieldSpec("use_partial_tp", "chk_use_partial_tp", "check", _const(False)),
    FieldSpec("use_entry_scoring", "chk_use_entry_scoring", "check", _const(False)),
    FieldSpec("entry_score_threshold", "spin_entry_score_threshold", "spin", _cfg("ENTRY_SCORE_THRESHOLD")),
    FieldSpec("use_strategy_engine", "chk_use_strategy_engine", "check", _cfg("DEFAULT_USE_STRATEGY_ENGINE")),
    FieldSpec("strategy_mode", "combo_strategy_mode", "combo_data", _cfg("DEFAULT_STRATEGY_MODE")),
    FieldSpec("single_strategy", "combo_single_strategy", "combo_data", _cfg("DEFAULT_SINGLE_STRATEGY")),
    FieldSpec("engine_gate_policy", "combo_engine_gate_policy", "combo_data", _cfg("DEFAULT_ENGINE_GATE_POLICY")),
    FieldSpec("ensemble_threshold", "spin_ensemble_threshold", "spin", _cfg("DEFAULT_ENSEMBLE_THRESHOLD")),
    FieldSpec("active_strategies", "input_active_strategies", "text", lambda c: ",".join(c.DEFAULT_ACTIVE_STRATEGIES)),
    FieldSpec("strategy_weights", "input_strategy_weights", "text", _const("")),
    FieldSpec("use_volatility_targeting", "chk_use_volatility_targeting", "check", _cfg("DEFAULT_USE_VOLATILITY_TARGETING")),
    FieldSpec("target_vol_pct", "spin_target_vol", "spin", _cfg("DEFAULT_TARGET_VOL_PCT")),
    FieldSpec("use_regime_filter", "chk_use_regime_filter", "check", _cfg("DEFAULT_USE_REGIME_FILTER")),
    FieldSpec("regime_min_adx", "spin_regime_min_adx", "spin", _cfg("DEFAULT_REGIME_MIN_ADX")),
    FieldSpec("use_drawdown_guard", "chk_use_drawdown_guard", "check", _cfg("DEFAULT_USE_DRAWDOWN_GUARD")),
    FieldSpec("drawdown_guard_pct", "spin_drawdown_guard", "spin", _cfg("DEFAULT_DRAWDOWN_GUARD_PCT")),
    FieldSpec("max_consecutive_losses", "spin_max_consecutive_losses", "spin", _cfg("DEFAULT_MAX_CONSECUTIVE_LOSSES")),
    FieldSpec("enable_account_wide_sync", "chk_enable_account_wide_sync", "check", _cfg("DEFAULT_ENABLE_ACCOUNT_WIDE_SYNC")),
    FieldSpec("risk_include_unrealized", "chk_risk_include_unrealized", "check", _cfg("DEFAULT_RISK_INCLUDE_UNREALIZED")),
    FieldSpec(
        "risk_include_external_holdings",
        "chk_risk_include_external_holdings",
        "check",
        _cfg("DEFAULT_RISK_INCLUDE_EXTERNAL_HOLDINGS"),
    ),
    FieldSpec("price_feed_stale_sec", "spin_price_feed_stale_sec", "spin", _cfg("DEFAULT_PRICE_FEED_STALE_SEC")),
    FieldSpec("manual_review_on_timeout", "chk_manual_review_on_timeout", "check", _cfg("DEFAULT_MANUAL_REVIEW_ON_TIMEOUT")),
    FieldSpec("use_risk_budget_sizing", "chk_use_risk_budget_sizing", "check", _cfg("DEFAULT_USE_RISK_BUDGET_SIZING")),
    FieldSpec("risk_budget_pct", "spin_risk_budget_pct", "spin", _cfg("DEFAULT_RISK_BUDGET_PCT")),
    FieldSpec("atr_stop_mult", "spin_atr_stop_mult", "spin", _cfg("DEFAULT_ATR_STOP_MULT")),
    FieldSpec("min_stop_pct", "spin_min_stop_pct", "spin", _cfg("DEFAULT_MIN_STOP_PCT")),
    FieldSpec("max_betting_pct", "spin_max_betting_pct", "spin", _cfg("DEFAULT_MAX_BETTING_PCT")),
    FieldSpec("use_kelly_adjustment", "chk_use_kelly_adjustment", "check", _cfg("DEFAULT_USE_KELLY_ADJUSTMENT")),
    FieldSpec("kelly_scale", "spin_kelly_scale", "spin", _cfg("DEFAULT_KELLY_SCALE")),
    FieldSpec("drawdown_state_enabled", "chk_drawdown_state_enabled", "check", _cfg("DEFAULT_DRAWDOWN_STATE_ENABLED")),
    FieldSpec("dd_caution_pct", "spin_dd_caution_pct", "spin", _cfg("DEFAULT_DD_CAUTION_PCT")),
    FieldSpec("dd_defense_pct", "spin_dd_defense_pct", "spin", _cfg("DEFAULT_DD_DEFENSE_PCT")),
    FieldSpec("dd_halt_pct", "spin_dd_halt_pct", "spin", _cfg("DEFAULT_DD_HALT_PCT")),
    FieldSpec("portfolio_corr_window", "spin_portfolio_corr_window", "spin", _cfg("DEFAULT_PORTFOLIO_CORR_WINDOW")),
    FieldSpec(
        "max_correlation_exposure_pct",
        "spin_max_correlation_exposure_pct",
        "spin",
        _cfg("DEFAULT_MAX_CORRELATION_EXPOSURE_PCT"),
    ),
    FieldSpec("use_execution_model", "chk_use_execution_model", "check", _cfg("DEFAULT_USE_EXECUTION_MODEL")),
    FieldSpec("execution_mode", "combo_execution_mode", "combo_data", _cfg("DEFAULT_EXECUTION_MODE")),
    FieldSpec("expected_slippage_guard_bps", "spin_expected_slippage_guard_bps", "spin", _cfg("DEFAULT_EXPECTED_SLIPPAGE_GUARD_BPS")),
    FieldSpec("twap_slices", "spin_twap_slices", "spin", _cfg("DEFAULT_TWAP_SLICES")),
    FieldSpec("twap_interval_sec", "spin_twap_interval_sec", "spin", _cfg("DEFAULT_TWAP_INTERVAL_SEC")),
    FieldSpec("use_meta_signal", "chk_use_meta_signal", "check", _cfg("DEFAULT_USE_META_SIGNAL")),
    FieldSpec("meta_min_expectancy", "spin_meta_min_expectancy", "spin", _cfg("DEFAULT_META_MIN_EXPECTANCY")),
    FieldSpec("meta_score_threshold", "spin_meta_score_threshold", "spin", _cfg("DEFAULT_META_SCORE_THRESHOLD")),
    FieldSpec("use_market_regime_filter", "chk_use_market_regime_filter", "check", _cfg("DEFAULT_USE_MARKET_REGIME_FILTER")),
    FieldSpec(
        "use_market_regime_risk_scaling",
        "chk_use_market_regime_risk_scaling",
        "check",
        _cfg("DEFAULT_USE_MARKET_REGIME_RISK_SCALING"),
    ),
    FieldSpec("market_regime_min_score", "spin_market_regime_min_score", "spin", _cfg("DEFAULT_MARKET_REGIME_MIN_SCORE")),
    FieldSpec("market_regime_refresh_sec", "spin_market_regime_refresh_sec", "spin", _cfg("DEFAULT_MARKET_REGIME_REFRESH_SEC")),
    FieldSpec("market_regime_top_n", "spin_market_regime_top_n", "spin", _cfg("DEFAULT_MARKET_REGIME_TOP_N")),
    FieldSpec(
        "market_regime_use_fear_greed",
        "chk_market_regime_use_fear_greed",
        "check",
        _cfg("DEFAULT_MARKET_REGIME_USE_FEAR_GREED"),
    ),
    FieldSpec(
        "market_regime_use_etf_flow",
        "chk_market_regime_use_etf_flow",
        "check",
        _cfg("DEFAULT_MARKET_REGIME_USE_ETF_FLOW"),
    ),
    FieldSpec(
        "fail_closed_on_stale_market_regime",
        "chk_fail_closed_on_stale_market_regime",
        "check",
        _cfg("DEFAULT_FAIL_CLOSED_ON_STALE_MARKET_REGIME"),
    ),
    FieldSpec("weight_rebalance_daily", "chk_weight_rebalance_daily", "check", _cfg("DEFAULT_WEIGHT_REBALANCE_DAILY")),
    FieldSpec("weight_min", "spin_weight_min", "spin", _cfg("DEFAULT_WEIGHT_MIN")),
    FieldSpec("weight_max", "spin_weight_max", "spin", _cfg("DEFAULT_WEIGHT_MAX")),
    FieldSpec("enable_discord_alerts", "chk_enable_discord_alerts", "check", _cfg("DEFAULT_ENABLE_DISCORD_ALERTS")),
    FieldSpec("discord_webhook", "input_discord_webhook", "text", _cfg("DEFAULT_DISCORD_WEBHOOK")),
    FieldSpec("persist_reconciliation_state", "chk_persist_reconciliation_state", "check", _cfg("DEFAULT_PERSIST_RECONCILIATION_STATE")),
    FieldSpec("paper_trading", "chk_paper_trading", "check", _cfg("DEFAULT_PAPER_TRADING")),
    FieldSpec("paper_allow_without_login", "chk_paper_allow_without_login", "check", _cfg("DEFAULT_PAPER_ALLOW_WITHOUT_LOGIN")),
    FieldSpec("paper_seed_krw", "spin_paper_seed_krw", "spin", _cfg("DEFAULT_PAPER_SEED_KRW")),
    FieldSpec("paper_fee_bps", "spin_paper_fee_bps", "spin", _cfg("DEFAULT_PAPER_FEE_BPS")),
    FieldSpec("paper_slippage_bps", "spin_paper_slippage_bps", "spin", _cfg("DEFAULT_PAPER_SLIPPAGE_BPS")),
)


def _read_widget_value(widget: Any, kind: str, default: Any) -> Any:
    if kind == "text":
        return widget.text().strip() if hasattr(widget, "text") else default
    if kind == "check":
        return bool(widget.isChecked()) if hasattr(widget, "isChecked") else bool(default)
    if kind == "spin":
        return widget.value() if hasattr(widget, "value") else default
    if kind == "combo_text":
        return widget.currentText() if hasattr(widget, "currentText") else default
    if kind == "combo_data":
        if hasattr(widget, "currentData"):
            value = widget.currentData()
            return default if value is None else value
    return default


def _write_widget_value(widget: Any, kind: str, value: Any) -> None:
    if kind == "text" and hasattr(widget, "setText"):
        widget.setText("" if value is None else str(value))
        return
    if kind == "check" and hasattr(widget, "setChecked"):
        widget.setChecked(bool(value))
        return
    if kind == "spin" and hasattr(widget, "setValue"):
        try:
            widget.setValue(value)
        except Exception:
            try:
                widget.setValue(float(value))
            except Exception:
                widget.setValue(int(float(value)))
        return
    if kind == "combo_text" and hasattr(widget, "setCurrentText"):
        widget.setCurrentText(str(value))
        return
    if kind == "combo_data" and hasattr(widget, "findData") and hasattr(widget, "setCurrentIndex"):
        idx = widget.findData(value)
        if idx >= 0:
            widget.setCurrentIndex(idx)


def collect_settings_from_specs(instance: Any, config: Any, specs: Iterable[FieldSpec] = COMMON_FIELD_SPECS) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for spec in specs:
        default = spec.default(config)
        widget = getattr(instance, spec.attr, None)
        if widget is None:
            payload[spec.key] = default
            continue
        try:
            payload[spec.key] = _read_widget_value(widget, spec.kind, default)
        except Exception:
            payload[spec.key] = default
    return payload


def apply_settings_to_widgets(instance: Any, settings: dict[str, Any], config: Any, specs: Iterable[FieldSpec] = COMMON_FIELD_SPECS) -> None:
    for spec in specs:
        widget = getattr(instance, spec.attr, None)
        if widget is None:
            continue
        value = settings.get(spec.key, spec.default(config))
        try:
            _write_widget_value(widget, spec.kind, value)
        except Exception:
            continue
