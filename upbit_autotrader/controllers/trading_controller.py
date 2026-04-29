import datetime
import time
from typing import Any, cast

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QMessageBox, QTableWidgetItem

from upbit_autotrader.controllers._type_support import ControllerTypeBase
from upbit_autotrader.controllers.trading_parts import (
    account_ops as _account_ops,
    execution_flow_ops as _execution_flow_ops,
    indicator_ops as _indicator_ops,
    lifecycle_ops as _lifecycle_ops,
    manual_review_ops as _manual_review_ops,
    market_regime_ops as _market_regime_ops,
    order_api_ops as _order_api_ops,
    risk_ops as _risk_ops,
    session_ops as _session_ops,
    signal_ops as _signal_ops,
    strategy_config_ops as _strategy_config_ops,
)
from upbit_autotrader.core.config import Config
from upbit_autotrader.market_regime import build_neutral_market_regime_output
from upbit_autotrader.risk.portfolio_risk import RiskLimitConfig, build_portfolio_risk_snapshot, evaluate_risk_limits
from upbit_autotrader.services.pyupbit_compat import pyupbit_fallback

try:
    import pandas as pd
except ImportError:
    pd = cast(Any, None)

try:
    import pyupbit
except ImportError:
    pyupbit = pyupbit_fallback


class TraderTradingController(ControllerTypeBase):
    login = _order_api_ops.login
    get_balance = _account_ops.get_balance

    _ensure_order_stability_state = _lifecycle_ops._ensure_order_stability_state
    _mark_reconciliation_dirty = _lifecycle_ops._mark_reconciliation_dirty
    _safe_parse_iso_datetime = staticmethod(_lifecycle_ops._safe_parse_iso_datetime)
    _emit_order_lifecycle_event = _lifecycle_ops._emit_order_lifecycle_event
    _build_reconciliation_state = _lifecycle_ops._build_reconciliation_state
    _persist_reconciliation_state = _lifecycle_ops._persist_reconciliation_state
    _load_reconciliation_state = _lifecycle_ops._load_reconciliation_state
    _persist_strategy_performance = _lifecycle_ops._persist_strategy_performance
    _transition_pending = _lifecycle_ops._transition_pending
    _register_manual_review = _lifecycle_ops._register_manual_review
    _register_orphan_event = _lifecycle_ops._register_orphan_event
    _handle_session_mismatch_terminal = _lifecycle_ops._handle_session_mismatch_terminal
    _ops_alert = _lifecycle_ops._ops_alert
    _next_trading_session = _lifecycle_ops._next_trading_session

    _get_toggle_value = _strategy_config_ops._get_toggle_value
    _get_spin_value = _strategy_config_ops._get_spin_value
    _get_engine_gate_policy = _strategy_config_ops._get_engine_gate_policy
    _enable_account_wide_sync = _strategy_config_ops._enable_account_wide_sync
    _risk_include_unrealized = _strategy_config_ops._risk_include_unrealized
    _risk_include_external_holdings = _strategy_config_ops._risk_include_external_holdings
    _manual_review_on_timeout = _strategy_config_ops._manual_review_on_timeout
    _price_feed_stale_sec = _strategy_config_ops._price_feed_stale_sec
    _use_risk_budget_sizing = _strategy_config_ops._use_risk_budget_sizing
    _use_kelly_adjustment = _strategy_config_ops._use_kelly_adjustment
    _drawdown_state_enabled = _strategy_config_ops._drawdown_state_enabled
    _portfolio_corr_window = _strategy_config_ops._portfolio_corr_window
    _max_correlation_exposure_pct = _strategy_config_ops._max_correlation_exposure_pct
    _use_execution_model = _strategy_config_ops._use_execution_model
    _execution_mode = _strategy_config_ops._execution_mode
    _use_meta_signal = _strategy_config_ops._use_meta_signal
    _meta_min_expectancy = _strategy_config_ops._meta_min_expectancy
    _meta_score_threshold = _strategy_config_ops._meta_score_threshold
    _weight_rebalance_daily = _strategy_config_ops._weight_rebalance_daily
    _weight_min = _strategy_config_ops._weight_min
    _weight_max = _strategy_config_ops._weight_max
    _risk_budget_pct = _strategy_config_ops._risk_budget_pct
    _atr_stop_mult = _strategy_config_ops._atr_stop_mult
    _min_stop_pct = _strategy_config_ops._min_stop_pct
    _max_betting_pct = _strategy_config_ops._max_betting_pct
    _kelly_scale = _strategy_config_ops._kelly_scale
    _drawdown_thresholds = _strategy_config_ops._drawdown_thresholds
    _get_execution_config = _strategy_config_ops._get_execution_config
    _is_mean_reversion_strategy = staticmethod(_strategy_config_ops._is_mean_reversion_strategy)
    _strategy_ids_for_gate = _strategy_config_ops._strategy_ids_for_gate
    _should_apply_legacy_entry_gate = _strategy_config_ops._should_apply_legacy_entry_gate
    _parse_active_strategy_ids = _strategy_config_ops._parse_active_strategy_ids
    _resolve_market_price = _strategy_config_ops._resolve_market_price
    _parse_strategy_weights = _strategy_config_ops._parse_strategy_weights
    _get_strategy_runtime_config = _strategy_config_ops._get_strategy_runtime_config

    _get_reserved_krw_total = _account_ops._get_reserved_krw_total
    _get_available_krw = _account_ops._get_available_krw
    _calculate_current_equity = _account_ops._calculate_current_equity
    _reserve_krw_for_buy = _account_ops._reserve_krw_for_buy
    _release_reserved_krw = _account_ops._release_reserved_krw
    _sync_reserved_with_pending = _account_ops._sync_reserved_with_pending
    _fetch_account_holdings = _account_ops._fetch_account_holdings
    _build_holdings_map = _account_ops._build_holdings_map
    _ensure_universe_row = _account_ops._ensure_universe_row
    _sync_account_holdings_to_universe = _account_ops._sync_account_holdings_to_universe
    _is_paper_mode = _account_ops._is_paper_mode
    _allow_paper_without_login = _account_ops._allow_paper_without_login
    _get_paper_seed_krw = _account_ops._get_paper_seed_krw
    _ensure_paper_service_state = _account_ops._ensure_paper_service_state
    _seed_paper_balance_once = _account_ops._seed_paper_balance_once

    _place_buy_order = _order_api_ops._place_buy_order
    _place_sell_order = _order_api_ops._place_sell_order
    _safe_log_order_error = _order_api_ops._safe_log_order_error
    _api_get_order = _order_api_ops._api_get_order
    _api_get_balance = _order_api_ops._api_get_balance
    _api_get_balances = _order_api_ops._api_get_balances
    _api_get_order_chance = _order_api_ops._api_get_order_chance
    _api_cancel_order = _order_api_ops._api_cancel_order
    _api_buy_market_order = _order_api_ops._api_buy_market_order
    _api_sell_market_order = _order_api_ops._api_sell_market_order
    _safe_get_order = _order_api_ops._safe_get_order
    api_call_with_retry = _order_api_ops.api_call_with_retry

    _start_twap_buy = _execution_flow_ops._start_twap_buy
    _run_next_twap_buy_slice = _execution_flow_ops._run_next_twap_buy_slice
    _schedule_next_twap_buy_slice = _execution_flow_ops._schedule_next_twap_buy_slice
    _reconcile_terminal_pending = _execution_flow_ops._reconcile_terminal_pending
    _resolve_timeout_pending = _execution_flow_ops._resolve_timeout_pending
    _reconcile_pending_orders = _execution_flow_ops._reconcile_pending_orders
    execute_buy = _execution_flow_ops.execute_buy
    check_buy_execution = _execution_flow_ops.check_buy_execution
    execute_sell = _execution_flow_ops.execute_sell
    _execute_partial_sell = _execution_flow_ops._execute_partial_sell
    _check_partial_sell_execution = _execution_flow_ops._check_partial_sell_execution
    check_sell_execution = _execution_flow_ops.check_sell_execution

    calculate_entry_score = _signal_ops.calculate_entry_score
    on_price_update = _signal_ops.on_price_update
    _check_buy_condition = _signal_ops._check_buy_condition
    _check_sell_condition = _signal_ops._check_sell_condition

    def _ensure_indicator_cache_state(self):
        if not hasattr(self, "_indicator_cache"):
            self._indicator_cache = {}
        if not hasattr(self, "_indicator_cache_ttl_sec"):
            self._indicator_cache_ttl_sec = dict(getattr(Config, "INDICATOR_CACHE_TTL_BY_INTERVAL", {}))

    def start_trading(self):
        _session_ops.bind_runtime(
            Config=Config,
            QMessageBox=QMessageBox,
            QTableWidgetItem=QTableWidgetItem,
            pyupbit=pyupbit,
            time=time,
        )
        return _session_ops.start_trading(self)

    def stop_trading(self):
        _session_ops.bind_runtime(
            Config=Config,
            QMessageBox=QMessageBox,
            QTableWidgetItem=QTableWidgetItem,
            pyupbit=pyupbit,
            time=time,
        )
        return _session_ops.stop_trading(self)

    def calculate_target_price(self, ticker, interval):
        _indicator_ops.bind_runtime(Config=Config, pd=pd, pyupbit=pyupbit, time=time)
        return _indicator_ops.calculate_target_price(self, ticker, interval)

    def calculate_ma(self, ticker, interval, period=5):
        _indicator_ops.bind_runtime(Config=Config, pd=pd, pyupbit=pyupbit, time=time)
        return _indicator_ops.calculate_ma(self, ticker, interval, period)

    def calculate_rsi(self, ticker, period=14):
        _indicator_ops.bind_runtime(Config=Config, pd=pd, pyupbit=pyupbit, time=time)
        return _indicator_ops.calculate_rsi(self, ticker, period)

    def calculate_macd(self, ticker):
        _indicator_ops.bind_runtime(Config=Config, pd=pd, pyupbit=pyupbit, time=time)
        return _indicator_ops.calculate_macd(self, ticker)

    def calculate_bollinger_bands(self, ticker):
        _indicator_ops.bind_runtime(Config=Config, pd=pd, pyupbit=pyupbit, time=time)
        return _indicator_ops.calculate_bollinger_bands(self, ticker)

    def calculate_atr(self, ticker, period=14):
        _indicator_ops.bind_runtime(Config=Config, pd=pd, pyupbit=pyupbit, time=time)
        return _indicator_ops.calculate_atr(self, ticker, period)

    def calculate_volume_avg(self, ticker, period=20):
        _indicator_ops.bind_runtime(Config=Config, pd=pd, pyupbit=pyupbit, time=time)
        return _indicator_ops.calculate_volume_avg(self, ticker, period)

    def calculate_stoch_rsi(self, ticker, rsi_period=14, stoch_period=14, k_period=3, d_period=3):
        _indicator_ops.bind_runtime(Config=Config, pd=pd, pyupbit=pyupbit, time=time)
        return _indicator_ops.calculate_stoch_rsi(self, ticker, rsi_period, stoch_period, k_period, d_period)

    def calculate_dmi_adx(self, ticker, period=14):
        _indicator_ops.bind_runtime(Config=Config, pd=pd, pyupbit=pyupbit, time=time)
        return _indicator_ops.calculate_dmi_adx(self, ticker, period)

    def _get_indicator_cache_ttl(self, interval):
        _indicator_ops.bind_runtime(Config=Config, pd=pd, pyupbit=pyupbit, time=time)
        return _indicator_ops._get_indicator_cache_ttl(self, interval)

    def _compute_rsi_from_close(self, close, period):
        _indicator_ops.bind_runtime(Config=Config, pd=pd, pyupbit=pyupbit, time=time)
        return _indicator_ops._compute_rsi_from_close(self, close, period)

    def _get_indicator_snapshot(self, ticker, interval, rsi_period=None, volume_period=None, bb_period=None):
        _indicator_ops.bind_runtime(Config=Config, pd=pd, pyupbit=pyupbit, time=time)
        return _indicator_ops._get_indicator_snapshot(self, ticker, interval, rsi_period, volume_period, bb_period)

    def _bind_market_regime_runtime(self):
        _market_regime_ops.bind_runtime(
            Config=Config,
            build_neutral_market_regime_output=build_neutral_market_regime_output,
        )

    def _ensure_market_regime_state(self):
        self._bind_market_regime_runtime()
        return _market_regime_ops._ensure_market_regime_state(self)

    def _get_market_regime_config(self):
        self._bind_market_regime_runtime()
        return _market_regime_ops._get_market_regime_config(self)

    def _get_market_regime_output(self):
        self._bind_market_regime_runtime()
        return _market_regime_ops._get_market_regime_output(self)

    def _capture_market_regime_fields(self, info=None):
        self._bind_market_regime_runtime()
        return _market_regime_ops._capture_market_regime_fields(self, info)

    def _resolve_market_regime_fields(self, pending=None, info=None):
        self._bind_market_regime_runtime()
        return _market_regime_ops._resolve_market_regime_fields(self, pending, info)

    def _apply_market_regime_filter(self, ticker):
        self._bind_market_regime_runtime()
        return _market_regime_ops._apply_market_regime_filter(self, ticker)

    def _apply_market_regime_risk_scaling(self, order_notional_krw):
        self._bind_market_regime_runtime()
        return _market_regime_ops._apply_market_regime_risk_scaling(self, order_notional_krw)

    def _update_market_regime_status(self):
        self._bind_market_regime_runtime()
        return _market_regime_ops._update_market_regime_status(self)

    def _on_market_regime_update(self, snapshot, output):
        self._bind_market_regime_runtime()
        return _market_regime_ops._on_market_regime_update(self, snapshot, output)

    def _get_risk_snapshot(self, force=False):
        _risk_ops.bind_runtime(
            Config=Config,
            RiskLimitConfig=RiskLimitConfig,
            build_portfolio_risk_snapshot=build_portfolio_risk_snapshot,
            evaluate_risk_limits=evaluate_risk_limits,
            pyupbit=pyupbit,
            time=time,
        )
        return _risk_ops._get_risk_snapshot(self, force)

    def check_risk_limits(self):
        _risk_ops.bind_runtime(
            Config=Config,
            RiskLimitConfig=RiskLimitConfig,
            build_portfolio_risk_snapshot=build_portfolio_risk_snapshot,
            evaluate_risk_limits=evaluate_risk_limits,
            pyupbit=pyupbit,
            time=time,
        )
        return _risk_ops.check_risk_limits(self)

    def _manual_review_age_text(self, age_sec):
        _manual_review_ops.bind_runtime(
            Config=Config,
            QColor=QColor,
            QMessageBox=QMessageBox,
            QTableWidgetItem=QTableWidgetItem,
            datetime=datetime,
        )
        return _manual_review_ops._manual_review_age_text(self, age_sec)

    def _manual_review_pending_state(self, payload):
        _manual_review_ops.bind_runtime(
            Config=Config,
            QColor=QColor,
            QMessageBox=QMessageBox,
            QTableWidgetItem=QTableWidgetItem,
            datetime=datetime,
        )
        return _manual_review_ops._manual_review_pending_state(self, payload)

    def _selected_manual_review_key(self):
        _manual_review_ops.bind_runtime(
            Config=Config,
            QColor=QColor,
            QMessageBox=QMessageBox,
            QTableWidgetItem=QTableWidgetItem,
            datetime=datetime,
        )
        return _manual_review_ops._selected_manual_review_key(self)

    def refresh_manual_review_table(self):
        _manual_review_ops.bind_runtime(
            Config=Config,
            QColor=QColor,
            QMessageBox=QMessageBox,
            QTableWidgetItem=QTableWidgetItem,
            datetime=datetime,
        )
        return _manual_review_ops.refresh_manual_review_table(self)

    def requery_selected_manual_review(self):
        _manual_review_ops.bind_runtime(
            Config=Config,
            QColor=QColor,
            QMessageBox=QMessageBox,
            QTableWidgetItem=QTableWidgetItem,
            datetime=datetime,
        )
        return _manual_review_ops.requery_selected_manual_review(self)

    def resolve_selected_manual_review(self):
        _manual_review_ops.bind_runtime(
            Config=Config,
            QColor=QColor,
            QMessageBox=QMessageBox,
            QTableWidgetItem=QTableWidgetItem,
            datetime=datetime,
        )
        return _manual_review_ops.resolve_selected_manual_review(self)

    def apply_preset(self, preset_type):
        if preset_type in Config.DEFAULT_PRESETS:
            self.apply_preset_values(Config.DEFAULT_PRESETS[preset_type])

    def set_table_item(self, row, col, text, bg_color):
        item = self.table.item(row, col)
        if item is None:
            item = QTableWidgetItem(text)
            self.table.setItem(row, col, item)
        else:
            item.setText(text)
        item.setBackground(QColor(bg_color))
        item.setForeground(QColor("#1a1a2e"))

    def _update_statistics(self):
        self.stat_trades.setText(f"📊 총 거래 횟수\n{self.trade_count} 회")
        winrate = (self.win_count / self.trade_count * 100) if self.trade_count > 0 else 0
        self.stat_winrate.setText(f"🎯 승률\n{winrate:.1f} %")
        self.stat_profit.setText(f"💰 총 실현손익\n{self.total_realized_profit:,.0f} 원")
        holdings = int(self._get_risk_snapshot(force=False).get("holdings_count", 0) or 0)
        self.stat_holdings.setText(f"📦 보유 종목\n{holdings} 개")

    def reset_statistics(self):
        reply = QMessageBox.question(
            self,
            "확인",
            "거래 통계를 초기화하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.total_realized_profit = 0
            self.trade_count = 0
            self.win_count = 0
            self._update_statistics()
            self.lbl_total_profit.setText("📈 당일 실현손익: 0 원")
            self.log("🔄 통계 초기화됨")

    def log(self, msg):
        t = datetime.datetime.now().strftime("[%H:%M:%S]")
        self.log_text.append(f"{t} {msg}")
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())
