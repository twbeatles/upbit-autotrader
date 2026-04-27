from __future__ import annotations

from typing import Any, cast

from upbit_autotrader.core.config import Config
from upbit_autotrader.execution.execution_model import ExecutionConfig
from upbit_autotrader.strategies.catalog import get_default_active_strategies, get_default_weights
from upbit_autotrader.strategies.engine import StrategyConfig
from upbit_autotrader.strategies.meta_signal import StrategyPerformanceTracker

try:
    import pyupbit
except ImportError:
    pyupbit = cast(Any, None)


def _get_toggle_value(self, attr_name, default_value):
    widget = getattr(self, attr_name, None)
    if widget is None or not hasattr(widget, "isChecked"):
        return bool(default_value)
    return bool(widget.isChecked())


def _get_spin_value(self, attr_name, default_value):
    widget = getattr(self, attr_name, None)
    if widget is None or not hasattr(widget, "value"):
        return float(default_value)
    try:
        return float(widget.value())
    except Exception:
        return float(default_value)


def _get_engine_gate_policy(self):
    combo = getattr(self, "combo_engine_gate_policy", None)
    if combo is not None and hasattr(combo, "currentData"):
        value = combo.currentData()
        if value:
            return str(value)
    return str(getattr(Config, "DEFAULT_ENGINE_GATE_POLICY", "strategy_aware"))


def _enable_account_wide_sync(self):
    return _get_toggle_value(
        self,
        "chk_enable_account_wide_sync",
        getattr(Config, "DEFAULT_ENABLE_ACCOUNT_WIDE_SYNC", True),
    )


def _risk_include_unrealized(self):
    return _get_toggle_value(
        self,
        "chk_risk_include_unrealized",
        getattr(Config, "DEFAULT_RISK_INCLUDE_UNREALIZED", True),
    )


def _risk_include_external_holdings(self):
    return _get_toggle_value(
        self,
        "chk_risk_include_external_holdings",
        getattr(Config, "DEFAULT_RISK_INCLUDE_EXTERNAL_HOLDINGS", True),
    )


def _manual_review_on_timeout(self):
    return _get_toggle_value(
        self,
        "chk_manual_review_on_timeout",
        getattr(Config, "DEFAULT_MANUAL_REVIEW_ON_TIMEOUT", True),
    )


def _price_feed_stale_sec(self):
    return _get_spin_value(
        self,
        "spin_price_feed_stale_sec",
        getattr(Config, "DEFAULT_PRICE_FEED_STALE_SEC", 15),
    )


def _use_risk_budget_sizing(self):
    return _get_toggle_value(
        self,
        "chk_use_risk_budget_sizing",
        getattr(Config, "DEFAULT_USE_RISK_BUDGET_SIZING", False),
    )


def _use_kelly_adjustment(self):
    return _get_toggle_value(
        self,
        "chk_use_kelly_adjustment",
        getattr(Config, "DEFAULT_USE_KELLY_ADJUSTMENT", False),
    )


def _drawdown_state_enabled(self):
    return _get_toggle_value(
        self,
        "chk_drawdown_state_enabled",
        getattr(Config, "DEFAULT_DRAWDOWN_STATE_ENABLED", False),
    )


def _portfolio_corr_window(self):
    return int(
        _get_spin_value(
            self,
            "spin_portfolio_corr_window",
            getattr(Config, "DEFAULT_PORTFOLIO_CORR_WINDOW", 60),
        )
    )


def _max_correlation_exposure_pct(self):
    return float(
        _get_spin_value(
            self,
            "spin_max_correlation_exposure_pct",
            getattr(Config, "DEFAULT_MAX_CORRELATION_EXPOSURE_PCT", 100.0),
        )
    )


def _use_execution_model(self):
    return _get_toggle_value(
        self,
        "chk_use_execution_model",
        getattr(Config, "DEFAULT_USE_EXECUTION_MODEL", False),
    )


def _execution_mode(self):
    combo = getattr(self, "combo_execution_mode", None)
    if combo is not None and hasattr(combo, "currentData"):
        value = combo.currentData()
        if value:
            return str(value)
    return str(getattr(Config, "DEFAULT_EXECUTION_MODE", "single_market"))


def _use_meta_signal(self):
    return _get_toggle_value(
        self,
        "chk_use_meta_signal",
        getattr(Config, "DEFAULT_USE_META_SIGNAL", False),
    )


def _meta_min_expectancy(self):
    return _get_spin_value(
        self,
        "spin_meta_min_expectancy",
        getattr(Config, "DEFAULT_META_MIN_EXPECTANCY", 0.0),
    )


def _meta_score_threshold(self):
    return _get_spin_value(
        self,
        "spin_meta_score_threshold",
        getattr(Config, "DEFAULT_META_SCORE_THRESHOLD", 60.0),
    )


def _weight_rebalance_daily(self):
    return _get_toggle_value(
        self,
        "chk_weight_rebalance_daily",
        getattr(Config, "DEFAULT_WEIGHT_REBALANCE_DAILY", True),
    )


def _weight_min(self):
    return _get_spin_value(self, "spin_weight_min", getattr(Config, "DEFAULT_WEIGHT_MIN", 0.5))


def _weight_max(self):
    return _get_spin_value(self, "spin_weight_max", getattr(Config, "DEFAULT_WEIGHT_MAX", 1.5))


def _risk_budget_pct(self):
    return _get_spin_value(
        self,
        "spin_risk_budget_pct",
        getattr(Config, "DEFAULT_RISK_BUDGET_PCT", 0.5),
    )


def _atr_stop_mult(self):
    return _get_spin_value(self, "spin_atr_stop_mult", getattr(Config, "DEFAULT_ATR_STOP_MULT", 2.0))


def _min_stop_pct(self):
    return _get_spin_value(self, "spin_min_stop_pct", getattr(Config, "DEFAULT_MIN_STOP_PCT", 0.3))


def _max_betting_pct(self):
    return _get_spin_value(
        self,
        "spin_max_betting_pct",
        getattr(Config, "DEFAULT_MAX_BETTING_PCT", 15.0),
    )


def _kelly_scale(self):
    return _get_spin_value(self, "spin_kelly_scale", getattr(Config, "DEFAULT_KELLY_SCALE", 0.25))


def _drawdown_thresholds(self):
    return (
        _get_spin_value(self, "spin_dd_caution_pct", getattr(Config, "DEFAULT_DD_CAUTION_PCT", 3.0)),
        _get_spin_value(self, "spin_dd_defense_pct", getattr(Config, "DEFAULT_DD_DEFENSE_PCT", 5.0)),
        _get_spin_value(self, "spin_dd_halt_pct", getattr(Config, "DEFAULT_DD_HALT_PCT", 8.0)),
    )


def _get_execution_config(self, fee_buy_bps=None, fee_sell_bps=None):
    mode = _execution_mode(self)
    spin_paper_fee_bps = getattr(self, "spin_paper_fee_bps", None)
    fee_bps = (
        float(spin_paper_fee_bps.value())
        if spin_paper_fee_bps is not None and hasattr(spin_paper_fee_bps, "value")
        else float(getattr(Config, "DEFAULT_PAPER_FEE_BPS", 5.0))
    )
    return ExecutionConfig(
        enabled=_use_execution_model(self),
        expected_slippage_guard_bps=_get_spin_value(
            self,
            "spin_expected_slippage_guard_bps",
            getattr(Config, "DEFAULT_EXPECTED_SLIPPAGE_GUARD_BPS", 30.0),
        ),
        twap_slices=int(_get_spin_value(self, "spin_twap_slices", getattr(Config, "DEFAULT_TWAP_SLICES", 3))),
        twap_interval_sec=int(
            _get_spin_value(self, "spin_twap_interval_sec", getattr(Config, "DEFAULT_TWAP_INTERVAL_SEC", 8))
        ),
        fee_bps=fee_bps,
        fee_buy_bps=float(fee_buy_bps) if fee_buy_bps is not None else None,
        fee_sell_bps=float(fee_sell_bps) if fee_sell_bps is not None else None,
        default_mode=str(mode),
        min_order_krw=5000.0,
    )


def _is_mean_reversion_strategy(strategy_id):
    return str(strategy_id or "") in {"rsi_reversion", "bollinger_reversion", "zscore_reversion"}


def _strategy_ids_for_gate(self, cfg):
    if cfg is None:
        return []
    if str(cfg.mode or "single") == "ensemble":
        return [sid for sid in list(cfg.active_strategies or []) if sid]
    return [str(cfg.single_strategy or "")]


def _should_apply_legacy_entry_gate(self, cfg):
    if cfg is None or not bool(getattr(cfg, "enabled", False)):
        return True
    policy = str(getattr(cfg, "entry_gate_policy", "") or _get_engine_gate_policy(self))
    if policy == "legacy_first":
        return True
    if policy == "engine_only":
        return False
    strategy_ids = _strategy_ids_for_gate(self, cfg)
    if not strategy_ids:
        return True
    if any(_is_mean_reversion_strategy(sid) for sid in strategy_ids):
        return False
    return True


def _parse_active_strategy_ids(self):
    text = self.input_active_strategies.text().strip() if hasattr(self, "input_active_strategies") else ""
    items = [s.strip() for s in text.split(",") if s.strip()]
    if not items:
        items = list(get_default_active_strategies())
    return items


def _parse_strategy_weights(self):
    raw = self.input_strategy_weights.text().strip() if hasattr(self, "input_strategy_weights") else ""
    parsed = {}
    if raw:
        for token in raw.split(","):
            token = token.strip()
            if not token or ":" not in token:
                continue
            sid, value = token.split(":", 1)
            sid = sid.strip()
            try:
                parsed[sid] = float(value.strip())
            except ValueError:
                continue
    defaults = get_default_weights()
    if not parsed:
        parsed = dict(defaults)
    for sid, weight in defaults.items():
        parsed.setdefault(sid, float(weight))
    if _weight_rebalance_daily(self):
        self._ensure_order_stability_state()
        tracker = getattr(self, "strategy_perf_tracker", None)
        if tracker is None:
            tracker = StrategyPerformanceTracker()
            self.strategy_perf_tracker = tracker
        if hasattr(tracker, "rebalance_weights_daily"):
            changed, new_weights = tracker.rebalance_weights_daily(
                parsed,
                weight_min=_weight_min(self),
                weight_max=_weight_max(self),
                ema_alpha=0.2,
            )
            if changed:
                parsed = dict(new_weights)
                if hasattr(self, "input_strategy_weights"):
                    text = ",".join(f"{k}:{v:.4f}" for k, v in parsed.items())
                    self.input_strategy_weights.setText(text)
                self._persist_strategy_performance()
    return parsed


def _get_strategy_runtime_config(self):
    enabled = (
        self.chk_use_strategy_engine.isChecked()
        if hasattr(self, "chk_use_strategy_engine")
        else Config.DEFAULT_USE_STRATEGY_ENGINE
    )
    mode = self.combo_strategy_mode.currentData() if hasattr(self, "combo_strategy_mode") else Config.DEFAULT_STRATEGY_MODE
    single_strategy = (
        self.combo_single_strategy.currentData()
        if hasattr(self, "combo_single_strategy")
        else Config.DEFAULT_SINGLE_STRATEGY
    )
    threshold = (
        self.spin_ensemble_threshold.value()
        if hasattr(self, "spin_ensemble_threshold")
        else Config.DEFAULT_ENSEMBLE_THRESHOLD
    )
    return StrategyConfig(
        enabled=bool(enabled),
        mode=str(mode or Config.DEFAULT_STRATEGY_MODE),
        single_strategy=str(single_strategy or Config.DEFAULT_SINGLE_STRATEGY),
        entry_gate_policy=_get_engine_gate_policy(self),
        ensemble_threshold=float(threshold),
        active_strategies=_parse_active_strategy_ids(self),
        weights=_parse_strategy_weights(self),
        use_volatility_targeting=(
            self.chk_use_volatility_targeting.isChecked()
            if hasattr(self, "chk_use_volatility_targeting")
            else Config.DEFAULT_USE_VOLATILITY_TARGETING
        ),
        use_regime_filter=(
            self.chk_use_regime_filter.isChecked()
            if hasattr(self, "chk_use_regime_filter")
            else Config.DEFAULT_USE_REGIME_FILTER
        ),
        use_drawdown_guard=(
            self.chk_use_drawdown_guard.isChecked()
            if hasattr(self, "chk_use_drawdown_guard")
            else Config.DEFAULT_USE_DRAWDOWN_GUARD
        ),
    )


def _resolve_market_price(self, ticker):
    info = self.universe.get(ticker, {}) if hasattr(self, "universe") else {}
    price = float(info.get("current", 0.0) or 0.0)
    if price > 0:
        return price
    if pyupbit is not None:
        try:
            fetched = pyupbit.get_current_price(ticker)
            if isinstance(fetched, (int, float)):
                return float(fetched)
        except Exception:
            return 0.0
    return 0.0
