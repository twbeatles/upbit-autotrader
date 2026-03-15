import datetime
import json
import os
import random
import time
from typing import Any, cast

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox

from upbit_autotrader.controllers._type_support import ControllerTypeBase
from upbit_autotrader.core.config import Config
from upbit_autotrader.core.entry_filter import should_enter_by_score
from upbit_autotrader.strategies.catalog import get_default_active_strategies, get_default_weights
from upbit_autotrader.strategies.engine import StrategyConfig
from upbit_autotrader.execution.execution_model import ExecutionConfig, estimate_realized_slippage_bps, plan_execution
from upbit_autotrader.risk.portfolio_risk import RiskLimitConfig, build_portfolio_risk_snapshot, evaluate_risk_limits
from upbit_autotrader.risk.position_sizing import PositionSizingInput, compute_position_size
from upbit_autotrader.strategies.meta_signal import MetaSignalInput, StrategyPerformanceTracker, evaluate_meta_signal
from upbit_autotrader.controllers.trading_parts import indicator_ops as _indicator_ops, manual_review_ops as _manual_review_ops, risk_ops as _risk_ops, session_ops as _session_ops

try:
    from upbit_autotrader.notifications.notifiers import EventType
except ImportError:
    EventType = None

try:
    import pandas as pd
    import pyupbit
except ImportError:
    pd = cast(Any, None)
    pyupbit = cast(Any, None)


class TraderTradingController(ControllerTypeBase):
    def login(self):
        """업비트 API 연결"""
        access = self.input_access.text().strip()
        secret = self.input_secret.text().strip()
        
        if not access or not secret:
            QMessageBox.warning(self, "경고", "API Access Key와 Secret Key를 입력해주세요.")
            return
        
        self.log("🔄 업비트 API 연결 시도 중...")
        self.lbl_connection.setText("● 연결 중...")
        self.lbl_connection.setStyleSheet("color: #ffc107; font-weight: bold;")
        
        try:
            self.upbit = pyupbit.Upbit(access, secret)
            balance = self._api_get_balance("KRW")
            
            if balance is not None:
                self.is_connected = True
                self.balance = float(balance)
                self.initial_balance = float(balance)
                self._paper_seeded = False
                self._seed_paper_balance_once()
                
                self.lbl_balance.setText(f"💰 주문가능금액: {float(balance):,.0f} 원")
                self.lbl_connection.setText("● 연결됨")
                self.lbl_connection.setStyleSheet("color: #00b894; font-weight: bold;")
                if hasattr(self, "refresh_trade_action_buttons"):
                    self.refresh_trade_action_buttons()
                
                self.log(f"✅ 업비트 API 연결 성공 (잔고: {float(balance):,.0f}원)")
                self.logger.info(f"API 연결 성공, 잔고: {float(balance):,.0f}원")
            else:
                raise Exception("잔고 조회 실패")
                
        except Exception as e:
            self.is_connected = False
            self.lbl_connection.setText("● 연결 실패")
            self.lbl_connection.setStyleSheet("color: #e63946; font-weight: bold;")
            self.log(f"❌ API 연결 실패: {e}")
            self.logger.error(f"API 연결 실패: {e}")
            if hasattr(self, "refresh_trade_action_buttons"):
                self.refresh_trade_action_buttons()
            QMessageBox.critical(self, "오류", f"API 연결에 실패했습니다.\n{e}")

    def get_balance(self):
        """잔고 조회"""
        if self._is_paper_mode():
            svc = self._ensure_paper_service_state()
            if svc is None:
                return
            self.balance = float(svc.get_krw_balance())
            self.lbl_balance.setText(f"💰 주문가능금액: {self.balance:,.0f} 원 [PAPER]")
            return

        if not self.upbit:
            return
        try:
            balance = self._api_get_balance("KRW")
            if balance is None:
                self.logger.warning("잔고 조회 결과가 None입니다.")
                return
            self.balance = float(balance)
            self.lbl_balance.setText(f"💰 주문가능금액: {self.balance:,.0f} 원")
        except Exception as e:
            self.logger.error(f"잔고 조회 실패: {e}")

    # ------------------------------------------------------------------
    # 매매 시작/중지
    # ------------------------------------------------------------------

    def start_trading(self):
        """매매 시작"""
        _session_ops.bind_runtime(
            Config=Config,
            QMessageBox=QMessageBox,
            QTableWidgetItem=QTableWidgetItem,
            pyupbit=pyupbit,
            time=time,
        )
        return _session_ops.start_trading(self)

    def stop_trading(self):
        """매매 중지"""
        _session_ops.bind_runtime(
            Config=Config,
            QMessageBox=QMessageBox,
            QTableWidgetItem=QTableWidgetItem,
            pyupbit=pyupbit,
            time=time,
        )
        return _session_ops.stop_trading(self)

    # ------------------------------------------------------------------
    # 전략 계산
    # ------------------------------------------------------------------

    def calculate_target_price(self, ticker, interval):
        """변동성 돌파 목표가 계산"""
        _indicator_ops.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            time=time,
        )
        return _indicator_ops.calculate_target_price(self, ticker, interval)

    def calculate_ma(self, ticker, interval, period=5):
        """이동평균 계산"""
        _indicator_ops.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            time=time,
        )
        return _indicator_ops.calculate_ma(self, ticker, interval, period)

    def calculate_rsi(self, ticker, period=14):
        """RSI 계산"""
        _indicator_ops.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            time=time,
        )
        return _indicator_ops.calculate_rsi(self, ticker, period)
    def calculate_macd(self, ticker):
        """MACD 계산 (MACD, Signal, Histogram 반환)"""
        _indicator_ops.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            time=time,
        )
        return _indicator_ops.calculate_macd(self, ticker)
    def calculate_bollinger_bands(self, ticker):
        """볼린저 밴드 계산 (상단, 중심, 하단 반환)"""
        _indicator_ops.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            time=time,
        )
        return _indicator_ops.calculate_bollinger_bands(self, ticker)
    def calculate_atr(self, ticker, period=14):
        """ATR (Average True Range) 계산"""
        _indicator_ops.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            time=time,
        )
        return _indicator_ops.calculate_atr(self, ticker, period)

    def calculate_volume_avg(self, ticker, period=20):
        """거래량 평균 계산"""
        _indicator_ops.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            time=time,
        )
        return _indicator_ops.calculate_volume_avg(self, ticker, period)
    def calculate_stoch_rsi(self, ticker, rsi_period=14, stoch_period=14, k_period=3, d_period=3):
        """스토캐스틱 RSI 계산 (v2.5 신규)"""
        _indicator_ops.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            time=time,
        )
        return _indicator_ops.calculate_stoch_rsi(self, ticker, rsi_period, stoch_period, k_period, d_period)

    def calculate_dmi_adx(self, ticker, period=14):
        """DMI와 ADX 계산 (v2.7) - 추세 강도 측정"""
        _indicator_ops.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            time=time,
        )
        return _indicator_ops.calculate_dmi_adx(self, ticker, period)

    def _ensure_indicator_cache_state(self):
        if not hasattr(self, '_indicator_cache'):
            self._indicator_cache = {}
        if not hasattr(self, '_indicator_cache_ttl_sec'):
            self._indicator_cache_ttl_sec = dict(getattr(Config, 'INDICATOR_CACHE_TTL_BY_INTERVAL', {}))
    def _ensure_order_stability_state(self):
        if not hasattr(self, "_reserved_krw_by_ticker"):
            self._reserved_krw_by_ticker = {}
        if not hasattr(self, "_active_session_id"):
            self._active_session_id = 0
        if not hasattr(self, "_order_error_log_ts"):
            self._order_error_log_ts = {}
        if not hasattr(self, "_manual_review_queue"):
            self._manual_review_queue = {}
        if not hasattr(self, "_orphan_events"):
            self._orphan_events = []
        if not hasattr(self, "_ops_alert_last_ts"):
            self._ops_alert_last_ts = {}
        if not hasattr(self, "_api_last_call_ts"):
            self._api_last_call_ts = 0.0
        if not hasattr(self, "_risk_snapshot_cache"):
            self._risk_snapshot_cache = {"ts": 0.0, "value": None}
        if not hasattr(self, "_last_price_update_ts"):
            self._last_price_update_ts = 0.0
        if not hasattr(self, "_price_feed_recovery_attempted"):
            self._price_feed_recovery_attempted = False
        if not hasattr(self, "_twap_buy_plans"):
            self._twap_buy_plans = {}
        if not hasattr(self, "_reconciliation_dirty"):
            self._reconciliation_dirty = False
        if not hasattr(self, "_manual_review_row_keys"):
            self._manual_review_row_keys = []
        if not hasattr(self, "persist_reconciliation_state"):
            self.persist_reconciliation_state = bool(getattr(Config, "DEFAULT_PERSIST_RECONCILIATION_STATE", False))
        if not hasattr(self, "strategy_perf_tracker") or self.strategy_perf_tracker is None:
            self.strategy_perf_tracker = StrategyPerformanceTracker()

    def _mark_reconciliation_dirty(self):
        self._ensure_order_stability_state()
        self._reconciliation_dirty = True

    @staticmethod
    def _safe_parse_iso_datetime(raw):
        try:
            return datetime.datetime.fromisoformat(str(raw or "").strip())
        except Exception:
            return None

    def _emit_order_lifecycle_event(
        self,
        event_type,
        *,
        ticker="",
        uuid="",
        session_id=0,
        state_from="",
        state_to="",
        reason="",
        source="",
        metadata=None,
    ):
        logger = getattr(self, "logger", None)
        try:
            path = str(getattr(Config, "ORDER_LIFECYCLE_LOG_FILE", "logs/order_lifecycle.jsonl") or "logs/order_lifecycle.jsonl")
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            payload = {
                "timestamp": datetime.datetime.now().isoformat(),
                "event_type": str(event_type or ""),
                "ticker": str(ticker or ""),
                "uuid": str(uuid or ""),
                "session_id": int(session_id or 0),
                "state_from": str(state_from or ""),
                "state_to": str(state_to or ""),
                "reason": str(reason or ""),
                "source": str(source or ""),
                "metadata": dict(metadata or {}),
            }
            with open(path, "a", encoding="utf-8") as fp:
                fp.write(json.dumps(payload, ensure_ascii=False))
                fp.write("\n")
        except Exception as exc:
            if logger is not None:
                logger.warning(f"order lifecycle 로그 저장 실패: {exc}")

    def _build_reconciliation_state(self):
        self._ensure_order_stability_state()
        pending = self.order_service.list_pending() if hasattr(self.order_service, "list_pending") else {}
        return {
            "pending_orders": pending,
            "manual_review_queue": dict(getattr(self, "_manual_review_queue", {}) or {}),
            "orphan_events": list(getattr(self, "_orphan_events", []) or []),
            "reserved_krw_by_ticker": dict(getattr(self, "_reserved_krw_by_ticker", {}) or {}),
            "active_session_id": int(getattr(self, "_active_session_id", 0) or 0),
        }

    def _persist_reconciliation_state(self, force=False):
        self._ensure_order_stability_state()
        if not bool(getattr(self, "persist_reconciliation_state", False)):
            return False
        if not force and not bool(getattr(self, "_reconciliation_dirty", False)):
            return False
        store = getattr(self, "reconciliation_store", None)
        if store is None or not hasattr(store, "save"):
            return False
        state = self._build_reconciliation_state()
        ok = bool(store.save(state))
        if ok:
            self._reconciliation_dirty = False
        return ok

    def _load_reconciliation_state(self):
        self._ensure_order_stability_state()
        if not bool(getattr(self, "persist_reconciliation_state", False)):
            return
        store = getattr(self, "reconciliation_store", None)
        if store is None or not hasattr(store, "load"):
            return
        payload = store.load() or {}
        pending_orders = payload.get("pending_orders", {})
        if hasattr(self, "order_service") and isinstance(pending_orders, dict):
            self.order_service.pending_orders = dict(pending_orders)
            self.pending_orders = self.order_service.pending_orders
        self._manual_review_queue = dict(payload.get("manual_review_queue", {}) or {})
        self._orphan_events = list(payload.get("orphan_events", []) or [])
        self._reserved_krw_by_ticker = {
            str(k): float(v or 0.0)
            for k, v in dict(payload.get("reserved_krw_by_ticker", {}) or {}).items()
        }
        self._active_session_id = int(payload.get("active_session_id", getattr(self, "_active_session_id", 0)) or 0)
        self._reconciliation_dirty = False
        if hasattr(self, "refresh_manual_review_table"):
            self.refresh_manual_review_table()

    def _persist_strategy_performance(self):
        tracker = getattr(self, "strategy_perf_tracker", None)
        if tracker is None or not hasattr(tracker, "save"):
            return False
        return bool(tracker.save(getattr(Config, "STRATEGY_PERF_FILE", "strategy_performance.json")))

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
        return self._get_toggle_value(
            "chk_enable_account_wide_sync",
            getattr(Config, "DEFAULT_ENABLE_ACCOUNT_WIDE_SYNC", True),
        )

    def _risk_include_unrealized(self):
        return self._get_toggle_value(
            "chk_risk_include_unrealized",
            getattr(Config, "DEFAULT_RISK_INCLUDE_UNREALIZED", True),
        )

    def _risk_include_external_holdings(self):
        return self._get_toggle_value(
            "chk_risk_include_external_holdings",
            getattr(Config, "DEFAULT_RISK_INCLUDE_EXTERNAL_HOLDINGS", True),
        )

    def _manual_review_on_timeout(self):
        return self._get_toggle_value(
            "chk_manual_review_on_timeout",
            getattr(Config, "DEFAULT_MANUAL_REVIEW_ON_TIMEOUT", True),
        )

    def _price_feed_stale_sec(self):
        return self._get_spin_value(
            "spin_price_feed_stale_sec",
            getattr(Config, "DEFAULT_PRICE_FEED_STALE_SEC", 15),
        )

    def _use_risk_budget_sizing(self):
        return self._get_toggle_value("chk_use_risk_budget_sizing", getattr(Config, "DEFAULT_USE_RISK_BUDGET_SIZING", False))

    def _use_kelly_adjustment(self):
        return self._get_toggle_value("chk_use_kelly_adjustment", getattr(Config, "DEFAULT_USE_KELLY_ADJUSTMENT", False))

    def _drawdown_state_enabled(self):
        return self._get_toggle_value("chk_drawdown_state_enabled", getattr(Config, "DEFAULT_DRAWDOWN_STATE_ENABLED", False))

    def _portfolio_corr_window(self):
        return int(self._get_spin_value("spin_portfolio_corr_window", getattr(Config, "DEFAULT_PORTFOLIO_CORR_WINDOW", 60)))

    def _max_correlation_exposure_pct(self):
        return float(
            self._get_spin_value(
                "spin_max_correlation_exposure_pct",
                getattr(Config, "DEFAULT_MAX_CORRELATION_EXPOSURE_PCT", 100.0),
            )
        )

    def _use_execution_model(self):
        return self._get_toggle_value("chk_use_execution_model", getattr(Config, "DEFAULT_USE_EXECUTION_MODEL", False))

    def _execution_mode(self):
        combo = getattr(self, "combo_execution_mode", None)
        if combo is not None and hasattr(combo, "currentData"):
            v = combo.currentData()
            if v:
                return str(v)
        return str(getattr(Config, "DEFAULT_EXECUTION_MODE", "single_market"))

    def _use_meta_signal(self):
        return self._get_toggle_value("chk_use_meta_signal", getattr(Config, "DEFAULT_USE_META_SIGNAL", False))

    def _meta_min_expectancy(self):
        return self._get_spin_value("spin_meta_min_expectancy", getattr(Config, "DEFAULT_META_MIN_EXPECTANCY", 0.0))

    def _meta_score_threshold(self):
        return self._get_spin_value("spin_meta_score_threshold", getattr(Config, "DEFAULT_META_SCORE_THRESHOLD", 60.0))

    def _weight_rebalance_daily(self):
        return self._get_toggle_value("chk_weight_rebalance_daily", getattr(Config, "DEFAULT_WEIGHT_REBALANCE_DAILY", True))

    def _weight_min(self):
        return self._get_spin_value("spin_weight_min", getattr(Config, "DEFAULT_WEIGHT_MIN", 0.5))

    def _weight_max(self):
        return self._get_spin_value("spin_weight_max", getattr(Config, "DEFAULT_WEIGHT_MAX", 1.5))

    def _risk_budget_pct(self):
        return self._get_spin_value("spin_risk_budget_pct", getattr(Config, "DEFAULT_RISK_BUDGET_PCT", 0.5))

    def _atr_stop_mult(self):
        return self._get_spin_value("spin_atr_stop_mult", getattr(Config, "DEFAULT_ATR_STOP_MULT", 2.0))

    def _min_stop_pct(self):
        return self._get_spin_value("spin_min_stop_pct", getattr(Config, "DEFAULT_MIN_STOP_PCT", 0.3))

    def _max_betting_pct(self):
        return self._get_spin_value("spin_max_betting_pct", getattr(Config, "DEFAULT_MAX_BETTING_PCT", 15.0))

    def _kelly_scale(self):
        return self._get_spin_value("spin_kelly_scale", getattr(Config, "DEFAULT_KELLY_SCALE", 0.25))

    def _drawdown_thresholds(self):
        return (
            self._get_spin_value("spin_dd_caution_pct", getattr(Config, "DEFAULT_DD_CAUTION_PCT", 3.0)),
            self._get_spin_value("spin_dd_defense_pct", getattr(Config, "DEFAULT_DD_DEFENSE_PCT", 5.0)),
            self._get_spin_value("spin_dd_halt_pct", getattr(Config, "DEFAULT_DD_HALT_PCT", 8.0)),
        )

    def _get_execution_config(self):
        mode = self._execution_mode()
        spin_paper_fee_bps = getattr(self, "spin_paper_fee_bps", None)
        fee_bps = (
            float(spin_paper_fee_bps.value())
            if spin_paper_fee_bps is not None and hasattr(spin_paper_fee_bps, "value")
            else float(getattr(Config, "DEFAULT_PAPER_FEE_BPS", 5.0))
        )
        return ExecutionConfig(
            enabled=self._use_execution_model(),
            expected_slippage_guard_bps=self._get_spin_value(
                "spin_expected_slippage_guard_bps",
                getattr(Config, "DEFAULT_EXPECTED_SLIPPAGE_GUARD_BPS", 30.0),
            ),
            twap_slices=int(self._get_spin_value("spin_twap_slices", getattr(Config, "DEFAULT_TWAP_SLICES", 3))),
            twap_interval_sec=int(self._get_spin_value("spin_twap_interval_sec", getattr(Config, "DEFAULT_TWAP_INTERVAL_SEC", 8))),
            fee_bps=fee_bps,
            default_mode=str(mode),
            min_order_krw=5000.0,
        )

    def _start_twap_buy(self, ticker, curr_price, slices, session_id):
        self._ensure_order_stability_state()
        if not slices:
            return False
        self._twap_buy_plans[ticker] = {
            "slices": [float(v) for v in slices if float(v) > 0],
            "next_idx": 0,
            "interval_sec": int(self._get_spin_value("spin_twap_interval_sec", getattr(Config, "DEFAULT_TWAP_INTERVAL_SEC", 8))),
            "session_id": int(session_id or 0),
            "curr_price": float(curr_price or 0.0),
        }
        return self._run_next_twap_buy_slice(ticker)

    def _run_next_twap_buy_slice(self, ticker):
        self._ensure_order_stability_state()
        plan = dict(getattr(self, "_twap_buy_plans", {}).get(ticker, {}) or {})
        if not plan:
            return False
        if self.order_service.has_pending(ticker):
            return False

        slices = list(plan.get("slices", []) or [])
        idx = int(plan.get("next_idx", 0) or 0)
        if idx >= len(slices):
            self._twap_buy_plans.pop(ticker, None)
            return False

        amount = float(slices[idx] or 0.0)
        if amount < 5000.0:
            plan["next_idx"] = idx + 1
            self._twap_buy_plans[ticker] = plan
            return self._run_next_twap_buy_slice(ticker)

        session_id = int(plan.get("session_id", 0) or 0)
        if not self._reserve_krw_for_buy(ticker, amount, session_id=session_id):
            self.log(f"[{ticker}] TWAP 가용 잔고 부족으로 중단")
            self._twap_buy_plans.pop(ticker, None)
            return False

        ok, result, err_msg = self._place_buy_order(
            ticker,
            amount,
            session_id=session_id,
            source=f"twap_buy_{idx + 1}/{len(slices)}",
        )
        if not ok or not result or "uuid" not in result:
            self._release_reserved_krw(ticker)
            self.log(f"[ERROR] [{ticker}] TWAP 매수 주문 실패: {err_msg}")
            self._twap_buy_plans.pop(ticker, None)
            return False

        if hasattr(self.order_service, "update_pending"):
            self.order_service.update_pending(
                ticker,
                execution_mode="twap_market",
                twap_slice_index=int(idx + 1),
                twap_slice_count=int(len(slices)),
            )
        self._mark_reconciliation_dirty()

        info = self.universe.get(ticker)
        if info:
            info["state"] = "주문중"
            self.set_table_item(info["row"], 4, "⏳ 주문중", "#ffc107")

        plan["next_idx"] = idx + 1
        self._twap_buy_plans[ticker] = plan
        self.log(f"📤 [{ticker}] TWAP 매수 {idx + 1}/{len(slices)}: {amount:,.0f}원")
        QTimer.singleShot(
            2000,
            lambda t=ticker, u=result["uuid"], s=session_id: self.check_buy_execution(
                t, u, retry_count=0, session_id=s
            ),
        )
        return True

    def _schedule_next_twap_buy_slice(self, ticker):
        self._ensure_order_stability_state()
        plan = self._twap_buy_plans.get(ticker)
        if not plan:
            return
        if self.order_service.has_pending(ticker):
            return
        idx = int(plan.get("next_idx", 0) or 0)
        total = len(plan.get("slices", []) or [])
        if idx >= total:
            self._twap_buy_plans.pop(ticker, None)
            self.log(f"✅ [{ticker}] TWAP 매수 시퀀스 완료")
            return
        delay_ms = int(max(0, int(plan.get("interval_sec", 8) or 8)) * 1000)
        QTimer.singleShot(delay_ms, lambda t=ticker: self._run_next_twap_buy_slice(t))

    @staticmethod
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
        policy = str(getattr(cfg, "entry_gate_policy", "") or self._get_engine_gate_policy())
        if policy == "legacy_first":
            return True
        if policy == "engine_only":
            return False
        strategy_ids = self._strategy_ids_for_gate(cfg)
        if not strategy_ids:
            return True
        if any(self._is_mean_reversion_strategy(sid) for sid in strategy_ids):
            return False
        return True

    def _transition_pending(self, ticker, next_state, reason="", metadata=None):
        if not hasattr(self, "order_service") or not hasattr(self.order_service, "transition_pending"):
            return False
        pending_before = self.order_service.get_pending(ticker) if hasattr(self.order_service, "get_pending") else None
        state_from = str((pending_before or {}).get("lifecycle_state", ""))
        transitioned = bool(
            self.order_service.transition_pending(
                ticker=ticker,
                next_state=next_state,
                reason=reason,
                metadata=metadata or {},
            )
        )
        if transitioned:
            pending_after = self.order_service.get_pending(ticker) if hasattr(self.order_service, "get_pending") else None
            self._mark_reconciliation_dirty()
            self._emit_order_lifecycle_event(
                "pending_transition",
                ticker=ticker,
                uuid=(pending_after or pending_before or {}).get("uuid", ""),
                session_id=(pending_after or pending_before or {}).get("session_id", 0),
                state_from=state_from,
                state_to=str(next_state or ""),
                reason=reason,
                source=(pending_after or pending_before or {}).get("source", ""),
                metadata=metadata or {},
            )
        return transitioned

    def _register_manual_review(self, ticker, uuid, reason, order=None, extra=None):
        self._ensure_order_stability_state()
        if not self._manual_review_on_timeout():
            return
        pending = self.order_service.get_pending(ticker) if hasattr(self, "order_service") else None
        if pending and hasattr(self.order_service, "update_pending"):
            self.order_service.update_pending(ticker, needs_manual_review=True)
        self._transition_pending(ticker, "manual_review", reason=reason, metadata={"uuid": uuid})
        payload = {
            "ticker": ticker,
            "uuid": str(uuid or ""),
            "reason": reason,
            "queued_at": datetime.datetime.now().isoformat(),
            "pending": dict(pending or {}),
            "order": dict(order or {}),
            "extra": dict(extra or {}),
        }
        key = str(uuid or f"{ticker}:{payload['queued_at']}")
        self._manual_review_queue[key] = payload
        self._mark_reconciliation_dirty()
        self._emit_order_lifecycle_event(
            "manual_review_registered",
            ticker=ticker,
            uuid=uuid,
            session_id=(pending or {}).get("session_id", 0),
            state_from=str((pending or {}).get("lifecycle_state", "")),
            state_to="manual_review",
            reason=reason,
            source=(pending or {}).get("source", ""),
            metadata={"queue_key": key, "extra": dict(extra or {})},
        )
        self._ops_alert(
            level="warning",
            message=f"⚠️ [{ticker}] 수동검토 큐 적재: {reason}",
            key=f"manual_review:{ticker}:{key}",
            cooldown=30,
        )
        if hasattr(self, "refresh_manual_review_table"):
            self.refresh_manual_review_table()

    def _register_orphan_event(self, ticker, uuid, side, state, session_id, source):
        self._ensure_order_stability_state()
        event = {
            "timestamp": datetime.datetime.now().isoformat(),
            "ticker": ticker,
            "uuid": str(uuid or ""),
            "side": str(side or ""),
            "state": str(state or ""),
            "session_id": int(session_id or 0),
            "active_session_id": int(getattr(self, "_active_session_id", 0) or 0),
            "source": str(source or ""),
        }
        self._orphan_events.append(event)
        if len(self._orphan_events) > 500:
            self._orphan_events = self._orphan_events[-500:]
        self._mark_reconciliation_dirty()
        self._emit_order_lifecycle_event(
            "orphan_registered",
            ticker=ticker,
            uuid=uuid,
            session_id=session_id,
            state_from="",
            state_to=str(state or ""),
            reason="session_mismatch_orphan",
            source=source,
            metadata={"active_session_id": int(getattr(self, "_active_session_id", 0) or 0), "side": str(side or "")},
        )
        self._ops_alert(
            level="warning",
            message=f"⚠️ [{ticker}] 세션 불일치 orphan 이벤트 감지 ({state})",
            key=f"orphan:{event['uuid']}:{event['active_session_id']}",
            cooldown=20,
        )

    def _handle_session_mismatch_terminal(self, ticker, uuid, side, state, session_id, source):
        self._register_orphan_event(ticker, uuid, side, state, session_id, source)
        if str(state or "").lower() in ("done", "cancel"):
            if hasattr(self.order_service, "clear_pending_if_uuid"):
                self.order_service.clear_pending_if_uuid(ticker, uuid)
            else:
                self.order_service.clear_pending(ticker)
            if str(side or "").upper() == "BUY":
                self._release_reserved_krw(ticker)
            self._sync_account_holdings_to_universe(account_holdings=None, include_external=True)

    def _ops_alert(self, level, message, key, cooldown: float | int = 10):
        self._ensure_order_stability_state()
        now_ts = time.time()
        cache_key = str(key or message)
        last_ts = float(self._ops_alert_last_ts.get(cache_key, 0.0) or 0.0)
        if cooldown and (now_ts - last_ts) < float(cooldown):
            return
        self._ops_alert_last_ts[cache_key] = now_ts
        if hasattr(self, "log"):
            self.log(message)
        logger = getattr(self, "logger", None)
        if logger is not None:
            level = str(level or "info").lower()
            if level == "error":
                logger.error(message)
            elif level == "warning":
                logger.warning(message)
            else:
                logger.info(message)
        if hasattr(self, "send_notification"):
            try:
                self.send_notification("Upbit Pro Trader", message)
            except Exception:
                pass
        manager = getattr(self, "notification_manager", None)
        if manager is not None and EventType is not None and hasattr(manager, "notify"):
            try:
                level_l = str(level or "info").lower()
                event_type = EventType.INFO
                if level_l == "warning":
                    event_type = EventType.WARNING
                elif level_l == "error":
                    event_type = EventType.ERROR
                manager.notify(event_type, message)
            except Exception:
                pass
    def _next_trading_session(self):
        self._ensure_order_stability_state()
        self._active_session_id += 1
        self._mark_reconciliation_dirty()
        return self._active_session_id
    def _get_reserved_krw_total(self):
        self._ensure_order_stability_state()
        return sum(max(0.0, float(v or 0.0)) for v in self._reserved_krw_by_ticker.values())
    def _get_available_krw(self):
        balance = float(getattr(self, "balance", 0) or 0)
        return max(0.0, balance - self._get_reserved_krw_total())
    def _reserve_krw_for_buy(self, ticker, amount, session_id=0):
        self._ensure_order_stability_state()
        amount = float(amount or 0.0)
        if amount <= 0:
            return False
        existing = float(self._reserved_krw_by_ticker.get(ticker, 0.0) or 0.0)
        available = self._get_available_krw() + existing
        if amount > (available + 1e-8):
            return False
        self._reserved_krw_by_ticker[ticker] = amount
        self._mark_reconciliation_dirty()
        return True
    def _release_reserved_krw(self, ticker):
        self._ensure_order_stability_state()
        released = float(self._reserved_krw_by_ticker.pop(ticker, 0.0) or 0.0)
        if released > 0:
            self._mark_reconciliation_dirty()
        return released
    def _sync_reserved_with_pending(self):
        self._ensure_order_stability_state()
        if not hasattr(self, "order_service"):
            self._reserved_krw_by_ticker.clear()
            return
        if hasattr(self.order_service, "list_pending"):
            pending_tickers = set(self.order_service.list_pending().keys())
        else:
            pending_tickers = set(getattr(self, "pending_orders", {}).keys())
        for ticker in list(self._reserved_krw_by_ticker.keys()):
            if ticker not in pending_tickers:
                self._reserved_krw_by_ticker.pop(ticker, None)
        self._mark_reconciliation_dirty()

    def _fetch_account_holdings(self):
        if hasattr(self, "get_account_holdings"):
            try:
                return list(self.get_account_holdings() or [])
            except Exception as e:
                if hasattr(self, "logger"):
                    self.logger.warning(f"계좌 보유 조회 실패: {e}")
        return []

    def _build_holdings_map(self, account_holdings=None):
        holdings = list(account_holdings or [])
        holdings_map = {}
        for h in holdings:
            ticker = str(h.get("ticker") or "").strip()
            if not ticker:
                continue
            qty = float(h.get("qty", 0.0) or 0.0)
            buy_price = float(h.get("buy_price", 0.0) or 0.0)
            current_price = float(h.get("current_price", 0.0) or 0.0)
            if current_price <= 0:
                current_price = float(h.get("current", 0.0) or 0.0)
            value = float(h.get("value", qty * current_price) or 0.0)
            holdings_map[ticker] = {
                "ticker": ticker,
                "qty": qty,
                "buy_price": buy_price,
                "current_price": current_price,
                "value": value,
            }
        return holdings_map

    def _ensure_universe_row(self, ticker):
        info = self.universe.get(ticker)
        if info is None:
            row = len(self.universe)
            info = {
                "name": ticker,
                "state": "감시중",
                "row": row,
                "target": 0.0,
                "ma5": 0.0,
                "current": 0.0,
                "qty": 0.0,
                "buy_price": 0.0,
                "invest_amt": 0.0,
                "high_since_buy": 0.0,
                "max_profit_rate": 0.0,
                "partial_sold": [],
            }
            self.universe[ticker] = info
            if hasattr(self, "table"):
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(ticker))
                self.table.setItem(row, 1, QTableWidgetItem("-"))
                self.table.setItem(row, 2, QTableWidgetItem("-"))
                self.table.setItem(row, 3, QTableWidgetItem("-"))
                self.set_table_item(row, 4, "👀 감시중", "#00b894")
                self.table.setItem(row, 5, QTableWidgetItem("0.00000000"))
                self.table.setItem(row, 6, QTableWidgetItem("-"))
                self.table.setItem(row, 7, QTableWidgetItem("-"))
                self.table.setItem(row, 8, QTableWidgetItem("-"))
                self.table.setItem(row, 9, QTableWidgetItem("-"))
                info["ui_items"] = {
                    "price": self.table.item(row, 1),
                    "state": self.table.item(row, 4),
                    "qty": self.table.item(row, 5),
                    "buy_price": self.table.item(row, 6),
                    "profit": self.table.item(row, 7),
                    "max_profit": self.table.item(row, 8),
                    "invest": self.table.item(row, 9),
                }
        return info

    def _sync_account_holdings_to_universe(self, account_holdings=None, include_external=None):
        if not hasattr(self, "universe"):
            return
        include_external = self._enable_account_wide_sync() if include_external is None else bool(include_external)
        holdings_map = self._build_holdings_map(account_holdings or self._fetch_account_holdings())
        for ticker, h in holdings_map.items():
            if not include_external and ticker not in self.universe:
                continue
            info = self._ensure_universe_row(ticker)
            qty = float(h.get("qty", 0.0) or 0.0)
            buy_price = float(h.get("buy_price", 0.0) or 0.0)
            current = float(h.get("current_price", 0.0) or info.get("current", 0.0) or 0.0)
            info["qty"] = qty
            info["buy_price"] = buy_price
            info["current"] = current
            info["invest_amt"] = max(0.0, qty * buy_price)
            if qty > 0:
                info["state"] = "보유중"
                info["high_since_buy"] = max(current, buy_price)
                info.setdefault("partial_sold", [])
                self.set_table_item(info["row"], 4, "💼 보유중", "#00b4d8")
            else:
                info["state"] = "감시중"
                self.set_table_item(info["row"], 4, "👀 감시중", "#00b894")
            ui_items = info.get("ui_items", {})
            qty_item = ui_items.get("qty")
            if qty_item is None and hasattr(self, "table"):
                qty_item = QTableWidgetItem("0.00000000")
                self.table.setItem(info["row"], 5, qty_item)
                info.setdefault("ui_items", {})["qty"] = qty_item
            if qty_item is not None:
                qty_item.setText(f"{qty:.8f}" if qty > 0 else "0.00000000")
            buy_price_item = ui_items.get("buy_price")
            if buy_price_item is None and hasattr(self, "table"):
                buy_price_item = QTableWidgetItem("-")
                self.table.setItem(info["row"], 6, buy_price_item)
                info.setdefault("ui_items", {})["buy_price"] = buy_price_item
            if buy_price_item is not None:
                buy_price_item.setText(f"{buy_price:,.0f}" if buy_price > 0 else "-")
            invest_item = ui_items.get("invest")
            if invest_item is None and hasattr(self, "table"):
                invest_item = QTableWidgetItem("-")
                self.table.setItem(info["row"], 9, invest_item)
                info.setdefault("ui_items", {})["invest"] = invest_item
            if invest_item is not None:
                invest_item.setText(f"{info['invest_amt']:,.0f}" if info["invest_amt"] > 0 else "-")

        if include_external:
            held_tickers = {t for t, h in holdings_map.items() if float(h.get("qty", 0.0) or 0.0) > 0}
            for ticker, info in self.universe.items():
                if ticker in held_tickers:
                    continue
                if float(info.get("qty", 0.0) or 0.0) <= 0:
                    continue
                if self.order_service.has_pending(ticker):
                    continue
                info["qty"] = 0.0
                info["buy_price"] = 0.0
                info["invest_amt"] = 0.0
                info["high_since_buy"] = 0.0
                info["max_profit_rate"] = 0.0
                info["partial_sold"] = []
                info["state"] = "감시중"
                self.set_table_item(info["row"], 4, "👀 감시중", "#00b894")
        self._risk_snapshot_cache = {"ts": 0.0, "value": None}
    def _is_paper_mode(self):
        return bool(hasattr(self, "chk_paper_trading") and self.chk_paper_trading.isChecked())
    def _allow_paper_without_login(self):
        if hasattr(self, "chk_paper_allow_without_login"):
            return bool(self.chk_paper_allow_without_login.isChecked())
        return bool(getattr(Config, "DEFAULT_PAPER_ALLOW_WITHOUT_LOGIN", True))
    def _get_paper_seed_krw(self):
        if hasattr(self, "spin_paper_seed_krw"):
            return max(0.0, float(self.spin_paper_seed_krw.value() or 0.0))
        return float(getattr(Config, "DEFAULT_PAPER_SEED_KRW", 10_000_000) or 0.0)
    def _ensure_paper_service_state(self):
        svc = getattr(self, "paper_order_service", None)
        if svc is None:
            return None
        fee_bps = self.spin_paper_fee_bps.value() if hasattr(self, "spin_paper_fee_bps") else Config.DEFAULT_PAPER_FEE_BPS
        slip_bps = self.spin_paper_slippage_bps.value() if hasattr(self, "spin_paper_slippage_bps") else Config.DEFAULT_PAPER_SLIPPAGE_BPS
        if hasattr(svc, "set_cost_model"):
            svc.set_cost_model(fee_rate=float(fee_bps) / 10000.0, slippage_bps=float(slip_bps))
        return svc
    def _seed_paper_balance_once(self):
        if not self._is_paper_mode():
            return
        svc = self._ensure_paper_service_state()
        if svc is None:
            return
        try:
            if hasattr(self, "_paper_seeded") and self._paper_seeded:
                return
            seed = float(getattr(self, "balance", 0.0) or 0.0)
            if seed <= 0 and getattr(self, "upbit", None) and getattr(self, "is_connected", False):
                api_balance = self._api_get_balance("KRW")
                if api_balance is not None:
                    seed = float(api_balance)
            if seed <= 0:
                seed = self._get_paper_seed_krw()
            if seed > 0:
                svc.seed_balance(seed)
                if float(getattr(self, "balance", 0.0) or 0.0) <= 0:
                    self.balance = float(seed)
            self._paper_seeded = True
        except Exception:
            return
    def _parse_active_strategy_ids(self):
        text = self.input_active_strategies.text().strip() if hasattr(self, "input_active_strategies") else ""
        items = [s.strip() for s in text.split(",") if s.strip()]
        if not items:
            items = list(get_default_active_strategies())
        return items
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
        for sid, w in defaults.items():
            parsed.setdefault(sid, float(w))
        if self._weight_rebalance_daily():
            self._ensure_order_stability_state()
            tracker = getattr(self, "strategy_perf_tracker", None)
            if tracker is None:
                tracker = StrategyPerformanceTracker()
                self.strategy_perf_tracker = tracker
            if hasattr(tracker, "rebalance_weights_daily"):
                changed, new_weights = tracker.rebalance_weights_daily(
                    parsed,
                    weight_min=self._weight_min(),
                    weight_max=self._weight_max(),
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
        enabled = self.chk_use_strategy_engine.isChecked() if hasattr(self, "chk_use_strategy_engine") else Config.DEFAULT_USE_STRATEGY_ENGINE
        mode = self.combo_strategy_mode.currentData() if hasattr(self, "combo_strategy_mode") else Config.DEFAULT_STRATEGY_MODE
        single_strategy = self.combo_single_strategy.currentData() if hasattr(self, "combo_single_strategy") else Config.DEFAULT_SINGLE_STRATEGY
        threshold = self.spin_ensemble_threshold.value() if hasattr(self, "spin_ensemble_threshold") else Config.DEFAULT_ENSEMBLE_THRESHOLD
        cfg = StrategyConfig(
            enabled=bool(enabled),
            mode=str(mode or Config.DEFAULT_STRATEGY_MODE),
            single_strategy=str(single_strategy or Config.DEFAULT_SINGLE_STRATEGY),
            entry_gate_policy=self._get_engine_gate_policy(),
            ensemble_threshold=float(threshold),
            active_strategies=self._parse_active_strategy_ids(),
            weights=self._parse_strategy_weights(),
            use_volatility_targeting=self.chk_use_volatility_targeting.isChecked() if hasattr(self, "chk_use_volatility_targeting") else Config.DEFAULT_USE_VOLATILITY_TARGETING,
            use_regime_filter=self.chk_use_regime_filter.isChecked() if hasattr(self, "chk_use_regime_filter") else Config.DEFAULT_USE_REGIME_FILTER,
            use_drawdown_guard=self.chk_use_drawdown_guard.isChecked() if hasattr(self, "chk_use_drawdown_guard") else Config.DEFAULT_USE_DRAWDOWN_GUARD,
        )
        return cfg
    def _place_buy_order(self, ticker, krw_amount, session_id=0, source="auto_buy"):
        if self._is_paper_mode():
            svc = self._ensure_paper_service_state()
            self._seed_paper_balance_once()
            if svc is None:
                return False, None, "paper service unavailable"
            market_price = self._resolve_market_price(ticker)
            ok, result, err_msg = svc.place_buy_market(ticker, krw_amount, market_price)
            if ok and result and "uuid" in result:
                self.order_service.mark_pending(
                    ticker,
                    "BUY",
                    result["uuid"],
                    session_id=session_id,
                    source=source,
                    reserved_krw=krw_amount,
                )
                self._transition_pending(ticker, "wait", reason="buy_order_submitted")
                self._mark_reconciliation_dirty()
            return ok, result, err_msg
        if self.order_service.has_pending(ticker):
            pending = self.order_service.get_pending(ticker)
            return False, None, f"이미 {pending['side']} 주문이 대기 중입니다."
        result = self._api_buy_market_order(ticker, krw_amount)
        if result and "uuid" in result:
            self.order_service.mark_pending(
                ticker,
                "BUY",
                result["uuid"],
                session_id=session_id,
                source=source,
                reserved_krw=krw_amount,
            )
            self._transition_pending(ticker, "wait", reason="buy_order_submitted")
            self._mark_reconciliation_dirty()
            return True, result, ""
        return False, result, "매수 주문 응답이 비정상입니다."

    def _place_sell_order(self, ticker, qty, side="SELL", session_id=0, source="auto_sell"):
        if self._is_paper_mode():
            svc = self._ensure_paper_service_state()
            if svc is None:
                return False, None, "paper service unavailable"
            market_price = self._resolve_market_price(ticker)
            ok, result, err_msg = svc.place_sell_market(ticker, qty, market_price)
            if ok and result and "uuid" in result:
                self.order_service.mark_pending(
                    ticker,
                    side,
                    result["uuid"],
                    session_id=session_id,
                    source=source,
                )
                self._transition_pending(ticker, "wait", reason="sell_order_submitted")
                self._mark_reconciliation_dirty()
            return ok, result, err_msg
        if self.order_service.has_pending(ticker):
            pending = self.order_service.get_pending(ticker)
            return False, None, f"이미 {pending['side']} 주문이 대기 중입니다."
        result = self._api_sell_market_order(ticker, qty)
        if result and "uuid" in result:
            self.order_service.mark_pending(
                ticker,
                side,
                result["uuid"],
                session_id=session_id,
                source=source,
            )
            self._transition_pending(ticker, "wait", reason="sell_order_submitted")
            self._mark_reconciliation_dirty()
            return True, result, ""
        return False, result, "매도 주문 응답이 비정상입니다."
    def _safe_log_order_error(self, uuid, message):
        self._ensure_order_stability_state()
        now_ts = time.time()
        key = str(uuid)
        last_ts = float(self._order_error_log_ts.get(key, 0.0) or 0.0)
        if (now_ts - last_ts) < 5.0:
            return
        self._order_error_log_ts[key] = now_ts
        if hasattr(self, "logger"):
            self.logger.warning(message)

    def _api_get_order(self, uuid):
        if not uuid:
            return None
        if self._is_paper_mode():
            svc = self._ensure_paper_service_state()
            if svc is None:
                return None
            return svc.get_order(uuid)
        if not getattr(self, "upbit", None):
            return None
        try:
            return self.api_call_with_retry(self.upbit.get_order, uuid, operation_name=f"get_order:{uuid}")
        except Exception as e:
            self._safe_log_order_error(uuid, f"주문 상태 조회 실패 ({uuid}): {e}")
            return None

    def _api_get_balance(self, currency="KRW"):
        if self._is_paper_mode():
            svc = self._ensure_paper_service_state()
            if svc is None:
                return None
            if str(currency or "").upper() == "KRW":
                return float(svc.get_krw_balance())
            return 0.0
        if not getattr(self, "upbit", None):
            return None
        try:
            return self.api_call_with_retry(self.upbit.get_balance, currency, operation_name=f"get_balance:{currency}")
        except Exception:
            return None

    def _api_get_balances(self):
        if self._is_paper_mode():
            svc = self._ensure_paper_service_state()
            if svc is None:
                return []
            holdings = svc.get_holdings()
            result = [{"currency": "KRW", "balance": str(svc.get_krw_balance())}]
            for ticker, item in holdings.items():
                result.append(
                    {
                        "currency": str(ticker).replace("KRW-", ""),
                        "balance": str(item.get("qty", 0.0)),
                        "avg_buy_price": str(item.get("avg_buy_price", 0.0)),
                    }
                )
            return result
        if not getattr(self, "upbit", None):
            return []
        try:
            return list(self.api_call_with_retry(self.upbit.get_balances, operation_name="get_balances") or [])
        except Exception:
            return []

    def _api_cancel_order(self, uuid):
        if not uuid:
            return None
        if self._is_paper_mode():
            svc = self._ensure_paper_service_state()
            if svc is None:
                return None
            cancel_fn = getattr(svc, "cancel_order", None)
            if callable(cancel_fn):
                try:
                    return cancel_fn(uuid)
                except Exception:
                    return None
            return None
        if not getattr(self, "upbit", None):
            return None
        cancel_fn = getattr(self.upbit, "cancel_order", None)
        if not callable(cancel_fn):
            return None
        try:
            return self.api_call_with_retry(cancel_fn, uuid, operation_name=f"cancel_order:{uuid}")
        except Exception as e:
            self._safe_log_order_error(uuid, f"주문 취소 실패 ({uuid}): {e}")
            return None

    def _api_buy_market_order(self, ticker, krw_amount):
        if self._is_paper_mode():
            return None
        if not getattr(self, "upbit", None):
            return None
        return self.api_call_with_retry(
            self.upbit.buy_market_order,
            ticker,
            krw_amount,
            operation_name=f"buy_market_order:{ticker}",
        )

    def _api_sell_market_order(self, ticker, qty):
        if self._is_paper_mode():
            return None
        if not getattr(self, "upbit", None):
            return None
        return self.api_call_with_retry(
            self.upbit.sell_market_order,
            ticker,
            qty,
            operation_name=f"sell_market_order:{ticker}",
        )

    def _safe_get_order(self, uuid):
        return self._api_get_order(uuid)

    def _reconcile_terminal_pending(self, ticker, pending):
        side = str((pending or {}).get("side", "")).upper()
        uuid = (pending or {}).get("uuid")
        active_session = getattr(self, "_active_session_id", 0)
        clear_pending_if_uuid = getattr(getattr(self, "order_service", None), "clear_pending_if_uuid", None)
        release_reserved = getattr(self, "_release_reserved_krw", None)
        if side == "BUY":
            if ticker in getattr(self, "universe", {}):
                self.check_buy_execution(ticker, uuid, retry_count=0, session_id=active_session)
            else:
                external_buy = getattr(self, "_check_external_buy_execution", None)
                if callable(external_buy):
                    external_buy(
                        ticker,
                        uuid,
                        reason=str((pending or {}).get("source", "외부매수")),
                        retry_count=0,
                        session_id=active_session,
                    )
                else:
                    # Fallback for light test doubles without batch-controller mixin.
                    if callable(clear_pending_if_uuid):
                        clear_pending_if_uuid(ticker, uuid)
                    elif hasattr(self, "order_service"):
                        self.order_service.clear_pending(ticker)
                    if callable(release_reserved):
                        release_reserved(ticker)
            return
        if side == "PARTIAL_SELL":
            qty = float((pending or {}).get("requested_qty", 0.0) or 0.0)
            reason = str((pending or {}).get("sell_reason", "분할익절"))
            level = (pending or {}).get("partial_level")
            self._check_partial_sell_execution(
                ticker,
                uuid,
                qty,
                reason,
                level=level,
                retry_count=0,
                session_id=active_session,
            )
            return
        if ticker in getattr(self, "universe", {}) and float(self.universe.get(ticker, {}).get("qty", 0.0) or 0.0) > 0:
            reason = str((pending or {}).get("sell_reason", "재정합"))
            self.check_sell_execution(ticker, uuid, reason, retry_count=0, session_id=active_session)
            return
        external_sell = getattr(self, "_check_external_sell_execution", None)
        if callable(external_sell):
            external_sell(
                ticker,
                uuid,
                reason=str((pending or {}).get("sell_reason", "외부매도")),
                context_label=str((pending or {}).get("context_label", "외부 매도")),
                retry_count=0,
                session_id=active_session,
            )
        else:
            if callable(clear_pending_if_uuid):
                clear_pending_if_uuid(ticker, uuid)
            elif hasattr(self, "order_service"):
                self.order_service.clear_pending(ticker)

    def _resolve_timeout_pending(self, ticker, pending, reason):
        uuid = (pending or {}).get("uuid")
        side = str((pending or {}).get("side", "")).upper()
        transition_pending = getattr(self, "_transition_pending", None)
        ops_alert = getattr(self, "_ops_alert", None)
        register_manual_review = getattr(self, "_register_manual_review", None)
        cancel_order = getattr(self, "_api_cancel_order", None)
        safe_get_order = getattr(self, "_safe_get_order", None)
        clear_pending_if_uuid = getattr(getattr(self, "order_service", None), "clear_pending_if_uuid", None)
        clear_pending = getattr(getattr(self, "order_service", None), "clear_pending", None)

        if callable(transition_pending):
            transition_pending(ticker, "timeout", reason=reason, metadata={"uuid": uuid, "side": side})
        if callable(ops_alert):
            ops_alert(
                level="warning",
                message=f"⚠️ [{ticker}] 주문 타임아웃 감지 - 취소/재조회 시도",
                key=f"timeout:{uuid}",
                cooldown=15,
            )
        if callable(cancel_order):
            cancel_order(uuid)
        order_raw = safe_get_order(uuid) if callable(safe_get_order) else None
        order = order_raw if isinstance(order_raw, dict) else None
        state = str((order or {}).get("state", "")).lower()
        if state in ("done", "cancel"):
            if callable(transition_pending):
                transition_pending(ticker, state, reason="timeout_requery_terminal", metadata={"uuid": uuid})
            self._reconcile_terminal_pending(ticker, pending)
            return True
        if callable(register_manual_review):
            register_manual_review(ticker, uuid, reason=reason, order=order, extra={"side": side})
        else:
            # Backward-compatible fallback used by minimal tests.
            if callable(clear_pending_if_uuid):
                clear_pending_if_uuid(ticker, uuid)
            elif callable(clear_pending):
                clear_pending(ticker)
        return False

    def _reconcile_pending_orders(self, force=False):
        self._ensure_order_stability_state()
        if not hasattr(self, "order_service"):
            return
        if not self._is_paper_mode() and not getattr(self, "upbit", None):
            return
        now = datetime.datetime.now()
        stale_timeout = float(getattr(Config, "PENDING_STALE_TIMEOUT_SEC", 90))
        if hasattr(self.order_service, "list_pending"):
            pending_items = self.order_service.list_pending().items()
        else:
            pending_items = getattr(self, "pending_orders", {}).items()
        for ticker, pending in list(pending_items):
            uuid = pending.get("uuid")
            requested_at = pending.get("requested_at")
            if not isinstance(requested_at, datetime.datetime):
                requested_at = now
            age_sec = max(0.0, (now - requested_at).total_seconds())
            order = self._safe_get_order(uuid)
            prev_retry = int((pending or {}).get("retry_count", 0) or 0)
            self.order_service.update_pending(
                ticker,
                last_checked_at=now,
                retry_count=prev_retry + 1,
            )
            if not order:
                missing_order_count = int((pending or {}).get("missing_order_count", 0) or 0) + 1
                self.order_service.update_pending(
                    ticker,
                    missing_order_count=missing_order_count,
                )
                min_retry_threshold = max(3, int(getattr(Config, "API_MAX_RETRIES", 3)))
                should_escalate = age_sec >= stale_timeout and (force or missing_order_count >= min_retry_threshold)
                if should_escalate:
                    latest_pending = self.order_service.get_pending(ticker) or pending
                    self._resolve_timeout_pending(
                        ticker=ticker,
                        pending=latest_pending,
                        reason="reconcile_missing_exchange_state",
                    )
                continue
            self.order_service.update_pending(ticker, missing_order_count=0)
            state = str(order.get("state", "")).lower()
            if state in ("wait",):
                self._transition_pending(ticker, "wait", reason="reconcile_wait", metadata={"age_sec": age_sec})
                if force and age_sec >= stale_timeout:
                    self._resolve_timeout_pending(ticker, pending, reason="force_reconcile_timeout")
                continue
            if state in ("done", "cancel"):
                self._transition_pending(ticker, state, reason="reconcile_terminal", metadata={"age_sec": age_sec})
                self._reconcile_terminal_pending(ticker, pending)
                continue
            if force and age_sec >= stale_timeout:
                self._resolve_timeout_pending(ticker, pending, reason="reconcile_unknown_state_timeout")
        self._sync_reserved_with_pending()
        self._mark_reconciliation_dirty()
    def _get_indicator_cache_ttl(self, interval):
        _indicator_ops.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            time=time,
        )
        return _indicator_ops._get_indicator_cache_ttl(self, interval)
    def _compute_rsi_from_close(self, close, period):
        _indicator_ops.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            time=time,
        )
        return _indicator_ops._compute_rsi_from_close(self, close, period)
    def _get_indicator_snapshot(self, ticker, interval, rsi_period=None, volume_period=None, bb_period=None):
        _indicator_ops.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            time=time,
        )
        return _indicator_ops._get_indicator_snapshot(self, ticker, interval, rsi_period, volume_period, bb_period)
    def api_call_with_retry(self, func, *args, max_retries=None, delay=None, operation_name="", **kwargs):
        """중앙 API 재시도/백오프/레이트리밋 래퍼."""
        self._ensure_order_stability_state()
        max_retries = int(max_retries or getattr(Config, "API_MAX_RETRIES", 3))
        base_delay = float(delay if delay is not None else getattr(Config, "API_BACKOFF_BASE_SEC", Config.API_RETRY_DELAY))
        min_interval = float(getattr(Config, "API_MIN_INTERVAL_SEC", 0.0))
        jitter_max = float(getattr(Config, "API_BACKOFF_JITTER_SEC", 0.0))

        last_error = None
        for attempt in range(max_retries):
            try:
                wait_sec = max(0.0, min_interval - (time.time() - float(self._api_last_call_ts or 0.0)))
                if wait_sec > 0:
                    time.sleep(wait_sec)
                result = func(*args, **kwargs)
                self._api_last_call_ts = time.time()
                return result
            except Exception as e:
                last_error = e
                if attempt >= max_retries - 1:
                    break
                sleep_sec = base_delay * (2 ** attempt)
                if jitter_max > 0:
                    sleep_sec += random.uniform(0.0, jitter_max)
                if hasattr(self, "logger"):
                    label = operation_name or getattr(func, "__name__", "api_call")
                    self.logger.warning(
                        f"API 호출 실패 ({label}) 시도 {attempt + 1}/{max_retries}: {e}"
                    )
                time.sleep(max(0.0, sleep_sec))
        if hasattr(self, "logger"):
            label = operation_name or getattr(func, "__name__", "api_call")
            self.logger.error(f"API 호출 최종 실패 ({label}): {last_error}")
        if isinstance(last_error, BaseException):
            raise last_error
        raise RuntimeError(f"API 호출 최종 실패: {operation_name or getattr(func, '__name__', 'api_call')}")

    def calculate_entry_score(self, ticker, curr_price, info, snapshot=None):
        """진입 점수 계산 (v2.5 신규) - 0~100점"""
        score = 0
        reasons = []
        weights = Config.ENTRY_WEIGHTS
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        if snapshot is None:
            snapshot = self._get_indicator_snapshot(
                ticker,
                interval,
                rsi_period=self.spin_rsi_period.value(),
                volume_period=Config.DEFAULT_VOLUME_PERIOD,
                bb_period=Config.DEFAULT_BB_PERIOD,
            )
        
        # 1. 목표가 돌파 (필수 조건이지만 점수로도 반영)
        if curr_price >= info['target']:
            score += weights['target_break']
            reasons.append(f"+{weights['target_break']} 목표가 돌파")
        
        # 2. MA5 필터
        if curr_price >= info['ma5']:
            score += weights['ma_filter']
            reasons.append(f"+{weights['ma_filter']} MA5 위")
        
        # 3. RSI 최적 구간
        if self.chk_use_rsi.isChecked():
            rsi = snapshot.get("rsi", 50) if snapshot else 50
            if 30 <= rsi <= 70:
                score += weights['rsi_optimal']
                reasons.append(f"+{weights['rsi_optimal']} RSI {rsi:.1f} (최적)")
            elif rsi < 30:
                score += weights['rsi_optimal'] // 2  # 과매도는 절반 점수
                reasons.append(f"+{weights['rsi_optimal']//2} RSI {rsi:.1f} (과매도)")
        else:
            score += weights['rsi_optimal']  # RSI 미사용시 만점
        
        # 4. MACD 골든크로스
        if hasattr(self, 'chk_use_macd') and self.chk_use_macd.isChecked():
            if snapshot:
                macd = snapshot.get("macd", 0)
                signal = snapshot.get("signal", 0)
            else:
                macd, signal, _ = self.calculate_macd(ticker)
            if macd > signal:
                score += weights['macd_golden']
                reasons.append(f"+{weights['macd_golden']} MACD 골든크로스")
        else:
            score += weights['macd_golden']  # MACD 미사용시 만점
        
        # 5. 거래량 확인
        if self.chk_use_volume.isChecked():
            if snapshot:
                curr_vol = snapshot.get("current_volume")
                avg_vol = snapshot.get("avg_volume")
            else:
                curr_vol, avg_vol = self.calculate_volume_avg(ticker, Config.DEFAULT_VOLUME_PERIOD)
            if curr_vol and avg_vol:
                required_vol = avg_vol * self.spin_volume_mult.value()
                if curr_vol >= required_vol:
                    score += weights['volume_confirm']
                    reasons.append(f"+{weights['volume_confirm']} 거래량 충분")
        else:
            score += weights['volume_confirm']
        
        # 6. 볼린저 밴드 포지션
        if snapshot:
            upper = snapshot.get("bb_upper")
            middle = snapshot.get("bb_middle")
            lower = snapshot.get("bb_lower")
        else:
            upper, middle, lower = self.calculate_bollinger_bands(ticker)
        if lower and middle:
            if lower <= curr_price <= middle:  # 하단~중간: 최적
                score += weights['bb_position']
                reasons.append(f"+{weights['bb_position']} BB 최적 구간")
            elif middle < curr_price <= upper:  # 중간~상단: 절반
                score += weights['bb_position'] // 2
                reasons.append(f"+{weights['bb_position']//2} BB 중상단")
        
        return score, reasons

    # ------------------------------------------------------------------
    # 가격 업데이트 및 조건 확인
    # ------------------------------------------------------------------

    def on_price_update(self, prices):
        """실시간 가격 업데이트"""
        if not self.is_running:
            return
        self._ensure_order_stability_state()
        if prices:
            self._last_price_update_ts = time.time()
            self._price_feed_recovery_attempted = False

        self.table.setUpdatesEnabled(False)
        try:
            for ticker, price in prices.items():
                if ticker not in self.universe:
                    continue

                info = self.universe[ticker]
                info['current'] = price

                if self.strategy:
                    self.strategy.update_recent_price(ticker, price)

                # 현재가 UI 업데이트
                price_item = info.get('ui_items', {}).get('price')
                if price_item is None:
                    price_item = QTableWidgetItem("-")
                    self.table.setItem(info['row'], 1, price_item)
                    info.setdefault('ui_items', {})['price'] = price_item
                price_item.setText(f"{price:,.0f}")

                # 매수 로직
                if info['state'] == '감시중' and info['qty'] == 0:
                    self._check_buy_condition(ticker, price, info)

                # 매도 로직
                elif info['state'] == '보유중' and info['qty'] > 0:
                    self._check_sell_condition(ticker, price, info)
        finally:
            self.table.setUpdatesEnabled(True)

    def _check_buy_condition(self, ticker, curr, info):
        """매수 조건 확인"""
        if self.strategy:
            if not self.strategy.check_cooldown(ticker):
                return
            if not self.strategy.check_mtf_condition(ticker):
                return

        cfg = self._get_strategy_runtime_config() if hasattr(self, "_get_strategy_runtime_config") else None
        hard_gate_enabled = self._should_apply_legacy_entry_gate(cfg)

        if hard_gate_enabled:
            # 1. 목표가 돌파
            if curr < info['target']:
                return
            
            # 2. MA5 위
            if curr < info['ma5']:
                return

        if hard_gate_enabled and self.strategy and hasattr(self, 'chk_use_breakout_confirm') and self.chk_use_breakout_confirm.isChecked():
            confirm_ticks = self.spin_breakout_ticks.value() if hasattr(self, 'spin_breakout_ticks') else None
            if not self.strategy.check_breakout_confirmation(ticker, info['target'], confirm_ticks):
                return

        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        need_snapshot = (
            self.chk_use_rsi.isChecked()
            or (hasattr(self, 'chk_use_macd') and self.chk_use_macd.isChecked())
            or self.chk_use_volume.isChecked()
            or self.chk_use_entry_scoring.isChecked()
            or (hasattr(self, "chk_use_strategy_engine") and self.chk_use_strategy_engine.isChecked())
        )
        snapshot = None
        if need_snapshot:
            snapshot = self._get_indicator_snapshot(
                ticker,
                interval,
                rsi_period=self.spin_rsi_period.value(),
                volume_period=Config.DEFAULT_VOLUME_PERIOD,
                bb_period=Config.DEFAULT_BB_PERIOD,
            )
        
        # 3. RSI 필터
        if self.chk_use_rsi.isChecked():
            rsi = snapshot.get("rsi", 50) if snapshot else self.calculate_rsi(ticker, self.spin_rsi_period.value())
            if rsi >= self.spin_rsi_upper.value():
                self.log(f"[{ticker}] RSI {rsi:.1f} >= {self.spin_rsi_upper.value()} (과매수) 진입 보류")
                return
        
        # 4. MACD 필터 (골든크로스: MACD > Signal)
        if hasattr(self, 'chk_use_macd') and self.chk_use_macd.isChecked():
            if snapshot:
                macd = snapshot.get("macd", 0)
                signal = snapshot.get("signal", 0)
            else:
                macd, signal, _ = self.calculate_macd(ticker)
            if macd <= signal:
                self.log(f"[{ticker}] MACD {macd:.2f} <= Signal {signal:.2f} (하락세) 진입 보류")
                return
        
        # 5. 거래량 필터
        if self.chk_use_volume.isChecked():
            if snapshot:
                curr_vol = snapshot.get("current_volume")
                avg_vol = snapshot.get("avg_volume")
            else:
                curr_vol, avg_vol = self.calculate_volume_avg(ticker, Config.DEFAULT_VOLUME_PERIOD)
            if curr_vol and avg_vol:
                required_vol = avg_vol * self.spin_volume_mult.value()
                if curr_vol < required_vol:
                    self.log(f"[{ticker}] 거래량 부족 ({curr_vol:,.0f} < {required_vol:,.0f}) 진입 보류")
                    return
        
        # 6. 리스크 관리
        if not self.check_risk_limits():
            return
        
        # 7. 진입 점수 체크 (선택적)
        score = None
        if self.chk_use_entry_scoring.isChecked():
            score, reasons = self.calculate_entry_score(ticker, curr, info, snapshot=snapshot)
            threshold = self.spin_entry_score_threshold.value()
            if not should_enter_by_score(True, score, threshold):
                reason_summary = ", ".join(reasons[:3]) if reasons else "점수 근거 없음"
                self.log(
                    f"[{ticker}] 진입 점수 {score:.0f} < {threshold} 진입 보류 "
                    f"(근거: {reason_summary})"
                )
                return

        # 8. 전략 엔진 체크 (single/ensemble)
        strategy_signal = None
        strategy_id = "legacy"
        if cfg and cfg.enabled and hasattr(self, "strategy_engine"):
            snapshot = snapshot or self._get_indicator_snapshot(
                ticker,
                interval,
                rsi_period=self.spin_rsi_period.value(),
                volume_period=Config.DEFAULT_VOLUME_PERIOD,
                bb_period=Config.DEFAULT_BB_PERIOD,
            )
            strategy_signal = self.strategy_engine.evaluate_entry(ticker, curr, info, snapshot or {}, cfg)
            if strategy_signal.action != "BUY":
                reason_text = ", ".join(strategy_signal.reasons[:2]) if strategy_signal.reasons else "전략 점수 미충족"
                self.log(f"[{ticker}] 전략 엔진 보류: {reason_text}")
                return
            score = strategy_signal.score
            strategy_id = str(strategy_signal.strategy_id or "engine")
        elif cfg and cfg.enabled:
            strategy_id = str(cfg.single_strategy if str(cfg.mode) == "single" else "ensemble")
        elif score is not None:
            strategy_id = "entry_scoring"

        # 9. 메타 시그널 게이트 (선택적)
        meta_signal = None
        if self._use_meta_signal():
            self._ensure_order_stability_state()
            tracker = getattr(self, "strategy_perf_tracker", None)
            if tracker is None:
                tracker = StrategyPerformanceTracker()
                self.strategy_perf_tracker = tracker
            adx = float((snapshot or {}).get("adx", 20.0) or 20.0)
            realized_vol = float((snapshot or {}).get("realized_vol_pct", 0.0) or 0.0)
            regime_score = max(0.0, min(100.0, (adx / 40.0) * 100.0 - max(0.0, realized_vol - 5.0) * 2.0))
            meta_signal = evaluate_meta_signal(
                MetaSignalInput(
                    strategy_id=strategy_id,
                    engine_score=float(score if score is not None else 50.0),
                    regime_score=regime_score,
                    min_expectancy=self._meta_min_expectancy(),
                    score_threshold=self._meta_score_threshold(),
                ),
                tracker=tracker,
            )
            if not bool(meta_signal.gate_pass):
                self.log(
                    f"[{ticker}] 메타 시그널 보류: meta={meta_signal.meta_score:.1f}, "
                    f"expectancy={meta_signal.expected_value:.2f}"
                )
                return

        # 매수 실행
        info["last_strategy_id"] = strategy_id
        info["last_strategy_score"] = float(score if score is not None else 0.0)
        if meta_signal is not None:
            info["last_meta_score"] = float(meta_signal.meta_score)
            info["last_expectancy"] = float(meta_signal.expected_value)
        if score is None:
            self.log(f"[{ticker}] 진입 조건 충족")
        else:
            self.log(f"[{ticker}] 진입 조건 충족 (점수: {score:.0f})")
        self.execute_buy(ticker, curr)

    def _check_sell_condition(self, ticker, curr, info):
        """매도 조건 확인"""
        buy_p = info['buy_price']
        if buy_p == 0:
            return
        
        profit_rate = (curr - buy_p) / buy_p * 100
        
        # 최고가 갱신
        if curr > info['high_since_buy']:
            info['high_since_buy'] = curr
            info['max_profit_rate'] = profit_rate
        
        # UI 업데이트
        row = info['row']
        profit_item = info.get('ui_items', {}).get('profit')
        if profit_item is None:
            profit_item = QTableWidgetItem("-")
            self.table.setItem(row, 7, profit_item)
            info.setdefault('ui_items', {})['profit'] = profit_item
        profit_item.setText(f"{profit_rate:.2f}%")
        if profit_rate >= 0:
            profit_item.setForeground(QColor("#e63946"))
        else:
            profit_item.setForeground(QColor("#4361ee"))
        max_profit_item = info.get('ui_items', {}).get('max_profit')
        if max_profit_item is None:
            max_profit_item = QTableWidgetItem("-")
            self.table.setItem(row, 8, max_profit_item)
            info.setdefault('ui_items', {})['max_profit'] = max_profit_item
        max_profit_item.setText(f"{info['max_profit_rate']:.2f}%")
        
        # 1. 손절
        loss_limit = -self.spin_loss.value()
        if profit_rate <= loss_limit:
            self.log(f"🛑 [{ticker}] 손절 조건 ({profit_rate:.2f}%) → 매도")
            self.execute_sell(ticker, "손절")
            return

        # 1-1. v3.0: 시간 기반 청산
        if self.strategy and hasattr(self, 'spin_max_holding_hours'):
            if self.strategy.check_holding_time_exit(ticker, self.spin_max_holding_hours.value()):
                self.execute_sell(ticker, "시간청산")
                return

        # 1-2. 전략 엔진 기반 청산
        cfg = self._get_strategy_runtime_config() if hasattr(self, "_get_strategy_runtime_config") else None
        if cfg and cfg.enabled and hasattr(self, "strategy_engine"):
            interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
            snapshot = self._get_indicator_snapshot(
                ticker,
                interval,
                rsi_period=self.spin_rsi_period.value(),
                volume_period=Config.DEFAULT_VOLUME_PERIOD,
                bb_period=Config.DEFAULT_BB_PERIOD,
            )
            signal = self.strategy_engine.evaluate_exit(ticker, curr, info, snapshot or {}, cfg)
            if signal.action == "SELL":
                reason = signal.reasons[0] if signal.reasons else "전략청산"
                self.log(f"📉 [{ticker}] 전략 청산 신호 ({signal.strategy_id})")
                self.execute_sell(ticker, f"전략:{reason}")
                return
        
        # 2. 분할 익절 (v2.7 신규)
        if hasattr(self, 'chk_use_partial_tp') and self.chk_use_partial_tp.isChecked():
            partial_sold = info.get('partial_sold', [])
            for level in Config.PARTIAL_TAKE_PROFIT:
                rate = level['rate']
                sell_ratio = level['sell_ratio']
                
                # 이 레벨에서 이미 매도했는지 확인
                if rate in partial_sold:
                    continue
                
                # 수익률 조건 충족
                if profit_rate >= rate and sell_ratio > 0:
                    partial_qty = info['qty'] * (sell_ratio / 100)
                    if partial_qty * curr >= 5000:  # 최소 주문금액 확인
                        if self._execute_partial_sell(ticker, partial_qty, f"분할익절 {rate}%", level=rate):
                            self.log(f"💰 [{ticker}] {rate}% 도달 → {sell_ratio}% 분할 익절")
                            return  # 한 번에 하나의 분할 매도만
        
        # 3. 트레일링 스톱
        ts_start = self.spin_ts_start.value()
        ts_stop = self.spin_ts_stop.value()
        
        if info['max_profit_rate'] >= ts_start:
            drop = (info['high_since_buy'] - curr) / info['high_since_buy'] * 100
            if drop >= ts_stop:
                self.log(f"🎯 [{ticker}] 트레일링 스톱 (고점 대비 -{drop:.2f}%) → 이익 실현")
                self.execute_sell(ticker, "TS")

    # ------------------------------------------------------------------
    # 주문 실행
    # ------------------------------------------------------------------

    def execute_buy(self, ticker, curr_price):
        """매수 주문"""
        if not self.upbit and not self._is_paper_mode():
            return

        self._ensure_order_stability_state()
        if self.order_service.has_pending(ticker):
            pending = self.order_service.get_pending(ticker)
            self.log(f"[{ticker}] 중복 주문 방지: {pending['side']} 주문 대기 중")
            return

        info = self.universe.get(ticker, {})
        if self.strategy:
            base_ratio_pct = float(self.strategy.calculate_dynamic_position_size(ticker))
        else:
            base_ratio_pct = float(self.spin_betting.value())
        ratio = base_ratio_pct / 100.0
        cfg = self._get_strategy_runtime_config() if hasattr(self, "_get_strategy_runtime_config") else None
        candle_text = self.combo_candle.currentText() if hasattr(self, "combo_candle") else Config.DEFAULT_CANDLE
        interval = Config.CANDLE_INTERVALS.get(candle_text, "minute240")
        snapshot = None
        if cfg and cfg.enabled and hasattr(self, "strategy_engine"):
            snapshot = self._get_indicator_snapshot(
                ticker,
                interval,
                rsi_period=self.spin_rsi_period.value(),
                volume_period=Config.DEFAULT_VOLUME_PERIOD,
                bb_period=Config.DEFAULT_BB_PERIOD,
            )
            adjusted_pct = self.strategy_engine.evaluate_position_size(ratio * 100.0, snapshot or {}, cfg)
            ratio = adjusted_pct / 100.0
        available_krw = self._get_available_krw()
        bet_cash = available_krw * ratio

        # 확장 리스크 사이징
        if self._use_risk_budget_sizing():
            snapshot = snapshot or self._get_indicator_snapshot(
                ticker,
                interval,
                rsi_period=self.spin_rsi_period.value(),
                volume_period=Config.DEFAULT_VOLUME_PERIOD,
                bb_period=Config.DEFAULT_BB_PERIOD,
            )
            atr_val = float(self.calculate_atr(ticker, Config.DEFAULT_ATR_PERIOD) or 0.0)
            risk_state = str(self._get_risk_snapshot(force=False).get("risk_state", "normal"))
            strategy_id = str(info.get("last_strategy_id", "legacy"))
            tracker = getattr(self, "strategy_perf_tracker", None)
            if tracker is None:
                tracker = StrategyPerformanceTracker()
                self.strategy_perf_tracker = tracker
            perf = tracker.get(strategy_id)
            sizing_out = compute_position_size(
                PositionSizingInput(
                    use_risk_budget_sizing=True,
                    equity_krw=float(getattr(self, "initial_balance", 0.0) or 0.0),
                    available_krw=available_krw,
                    current_price=float(curr_price or 0.0),
                    atr_value=atr_val,
                    base_betting_pct=float(base_ratio_pct),
                    risk_budget_pct=self._risk_budget_pct(),
                    atr_stop_mult=self._atr_stop_mult(),
                    min_stop_pct=self._min_stop_pct(),
                    max_betting_pct=self._max_betting_pct(),
                    use_kelly_adjustment=self._use_kelly_adjustment(),
                    kelly_scale=self._kelly_scale(),
                    win_rate=(perf.wins / perf.sample_count) if perf.sample_count > 0 else 0.5,
                    avg_win_pct=float(perf.avg_win_pct),
                    avg_loss_pct=float(perf.avg_loss_pct),
                    drawdown_state=risk_state,
                )
            )
            bet_cash = min(float(sizing_out.order_notional_krw), available_krw)
            info["last_sizing"] = dict(sizing_out.details)
            info["last_risk_state"] = risk_state
            info["last_stop_distance_pct"] = float(sizing_out.stop_distance_pct)
            ratio = float(sizing_out.position_ratio_pct) / 100.0

        # 실행 계획(single/TWAP)
        execution_cfg = self._get_execution_config()
        realized_vol = float((snapshot or {}).get("realized_vol_pct", 0.0) or 0.0)
        execution_plan = plan_execution(
            execution_cfg,
            bet_cash,
            realized_vol_pct=realized_vol,
            force_mode=self._execution_mode(),
        )
        if execution_plan.blocked:
            self.log(f"[{ticker}] 실행 모델 차단: {execution_plan.reason}")
            return
        bet_cash = float(execution_plan.order_notional_krw or 0.0)
        info["last_execution_mode"] = execution_plan.mode
        info["last_expected_slippage_bps"] = float(execution_plan.expected_slippage_bps)
        info["last_breakeven_pct"] = float(execution_plan.breakeven_pct)
        
        if bet_cash < 5000:  # 업비트 최소 주문금액
            self.log(f"[{ticker}] 매수금액 부족 (최소 5,000원)")
            return
        session_id = getattr(self, "_active_session_id", 0)

        if execution_plan.mode == "twap_market" and len(execution_plan.slice_notionals) > 1:
            started = self._start_twap_buy(
                ticker=ticker,
                curr_price=curr_price,
                slices=execution_plan.slice_notionals,
                session_id=session_id,
            )
            if started:
                return
            self.log(f"[{ticker}] TWAP 시작 실패, 단일 시장가로 fallback")

        if not self._reserve_krw_for_buy(ticker, bet_cash, session_id=session_id):
            self.log(f"[{ticker}] 사용 가능 잔고 부족 (가용: {self._get_available_krw():,.0f}원)")
            return
        
        try:
            # 시장가 매수
            ok, result, err_msg = self._place_buy_order(
                ticker,
                bet_cash,
                session_id=session_id,
                source="auto_buy",
            )
            
            if ok and result and 'uuid' in result:
                if hasattr(self.order_service, "update_pending"):
                    self.order_service.update_pending(
                        ticker,
                        execution_mode=str(execution_plan.mode),
                        expected_slippage_bps=float(execution_plan.expected_slippage_bps),
                        breakeven_pct=float(execution_plan.breakeven_pct),
                        strategy_score=float(info.get("last_strategy_score", 0.0) or 0.0),
                        meta_score=float(info.get("last_meta_score", 0.0) or 0.0),
                        risk_state=str(info.get("last_risk_state", "normal")),
                    )
                if info:
                    info['state'] = '주문중'
                    self.set_table_item(info['row'], 4, "⏳ 주문중", "#ffc107")
                
                self.log(f"📤 [{ticker}] 매수 주문: {bet_cash:,.0f}원 ({execution_plan.mode})")
                self.logger.info(f"매수 주문: {ticker} {bet_cash:,.0f}원")
                
                # 체결 확인
                QTimer.singleShot(
                    2000,
                    lambda t=ticker, u=result['uuid'], s=session_id: self.check_buy_execution(
                        t, u, retry_count=0, session_id=s
                    ),
                )
            else:
                self._release_reserved_krw(ticker)
                self.log(f"[ERROR] 매수 주문 실패: {err_msg} / {result}")
                
        except Exception as e:
            self.order_service.clear_pending(ticker)
            self._release_reserved_krw(ticker)
            self.log(f"[ERROR] 매수 주문 실패: {e}")
            self.logger.error(f"매수 주문 실패 ({ticker}): {e}")

    def check_buy_execution(self, ticker, uuid, retry_count=0, session_id=None):
        """매수 체결 확인 (최대 30회 재시도, 60초 타임아웃)"""
        MAX_RETRIES = 30  # 최대 30회 (60초)
        if hasattr(self, "_ensure_order_stability_state"):
            self._ensure_order_stability_state()
        pending = self.order_service.get_pending(ticker)
        if not pending:
            return
        if pending and str(pending.get("uuid")) != str(uuid):
            return
        clear_pending_if_uuid = getattr(self.order_service, "clear_pending_if_uuid", None)
        mark_reconciliation = getattr(self, "_mark_reconciliation_dirty", None)
        release_reserved = getattr(self, "_release_reserved_krw", None)
        transition_pending = getattr(self, "_transition_pending", None)
        handle_session_mismatch = getattr(self, "_handle_session_mismatch_terminal", None)
        resolve_timeout_pending = getattr(self, "_resolve_timeout_pending", None)
        ops_alert = getattr(self, "_ops_alert", None)
        register_manual_review = getattr(self, "_register_manual_review", None)
        mark_reconciliation = getattr(self, "_mark_reconciliation_dirty", None)
        persist_strategy_performance = getattr(self, "_persist_strategy_performance", None)
        mark_reconciliation = getattr(self, "_mark_reconciliation_dirty", None)

        try:
            if hasattr(self, "_safe_get_order"):
                order_raw = self._safe_get_order(uuid)
            else:
                order_raw = self.upbit.get_order(uuid)
            order = order_raw if isinstance(order_raw, dict) else None
            state = str(order.get("state", "")).lower() if order else "wait"
            if pending and hasattr(self.order_service, "update_pending"):
                self.order_service.update_pending(
                    ticker,
                    last_checked_at=datetime.datetime.now(),
                    retry_count=int(pending.get("retry_count", 0) or 0) + 1,
                )
                if callable(transition_pending):
                    transition_pending(ticker, "wait", reason="buy_execution_poll")

            if session_id is not None and session_id != getattr(self, "_active_session_id", 0):
                if state in ("done", "cancel"):
                    if callable(handle_session_mismatch):
                        handle_session_mismatch(
                            ticker=ticker,
                            uuid=uuid,
                            side="BUY",
                            state=state,
                            session_id=session_id,
                            source="check_buy_execution",
                        )
                return

            if state == 'done':
                if callable(transition_pending):
                    transition_pending(ticker, "done", reason="buy_execution_done")
                info = self.universe.get(ticker)
                execution_mode = str((pending or {}).get("execution_mode", "single_market") or "single_market")
                expected_slippage_bps = float((pending or {}).get("expected_slippage_bps", 0.0) or 0.0)
                strategy_score = float((pending or {}).get("strategy_score", 0.0) or 0.0)
                meta_score = float((pending or {}).get("meta_score", 0.0) or 0.0)
                risk_state = str((pending or {}).get("risk_state", "normal") or "normal")

                # 체결 정보
                executed_volume, total_price, avg_price = self.order_service.get_buy_fill_metrics(order)

                if executed_volume > 0 and total_price > 0:
                    if info:
                        prev_qty = float(info.get('qty', 0.0) or 0.0)
                        prev_invest = float(info.get('invest_amt', 0.0) or 0.0)
                        if prev_qty > 0 and prev_invest > 0:
                            merged_qty = prev_qty + executed_volume
                            merged_invest = prev_invest + total_price
                            merged_avg = (merged_invest / merged_qty) if merged_qty > 0 else avg_price
                        else:
                            merged_qty = executed_volume
                            merged_invest = total_price
                            merged_avg = avg_price
                        info['qty'] = merged_qty
                        info['buy_price'] = merged_avg
                        info['invest_amt'] = merged_invest
                        info['high_since_buy'] = max(float(info.get('high_since_buy', 0.0) or 0.0), merged_avg)
                        info['max_profit_rate'] = 0.0
                        info.setdefault('partial_sold', [])
                        info['state'] = '보유중'

                        if self.strategy:
                            self.strategy.set_holding_start(ticker)
                            self.strategy.clear_recent_prices(ticker)
                            self.strategy.clear_partial_profit(ticker)

                        row = info['row']
                        qty_item = info.get('ui_items', {}).get('qty')
                        if qty_item is None:
                            qty_item = QTableWidgetItem("-")
                            self.table.setItem(row, 5, qty_item)
                            info.setdefault('ui_items', {})['qty'] = qty_item
                        qty_item.setText(f"{merged_qty:.8f}")

                        buy_price_item = info.get('ui_items', {}).get('buy_price')
                        if buy_price_item is None:
                            buy_price_item = QTableWidgetItem("-")
                            self.table.setItem(row, 6, buy_price_item)
                            info.setdefault('ui_items', {})['buy_price'] = buy_price_item
                        buy_price_item.setText(f"{merged_avg:,.0f}")

                        invest_item = info.get('ui_items', {}).get('invest')
                        if invest_item is None:
                            invest_item = QTableWidgetItem("-")
                            self.table.setItem(row, 9, invest_item)
                            info.setdefault('ui_items', {})['invest'] = invest_item
                        invest_item.setText(f"{merged_invest:,.0f}")
                        self.set_table_item(row, 4, "💼 보유중", "#00b4d8")

                    fee_krw = float(order.get("paid_fee", 0.0) or 0.0) if order else 0.0
                    ref_price = float((info or {}).get("current", avg_price) or avg_price)
                    realized_slippage_bps = estimate_realized_slippage_bps(ref_price, avg_price, side="buy")
                    self.log(f"✅ [{ticker}] 매수 체결: {executed_volume:.8f} @ {avg_price:,.0f}원")
                    self.add_trade_record(
                        ticker,
                        'BUY',
                        avg_price,
                        executed_volume,
                        0,
                        '매수 체결',
                        fee_krw=fee_krw,
                        expected_slippage_bps=expected_slippage_bps,
                        realized_slippage_bps=realized_slippage_bps,
                        execution_mode=execution_mode,
                        session_id=session_id,
                        risk_state=risk_state,
                        strategy_score=strategy_score,
                        meta_score=meta_score,
                    )
                    manager = getattr(self, "notification_manager", None)
                    if manager is not None and EventType is not None and hasattr(manager, "notify_buy"):
                        try:
                            manager.notify_buy(ticker, avg_price, executed_volume)
                        except Exception:
                            pass
                    self.get_balance()
                    self._risk_snapshot_cache = {"ts": 0.0, "value": None}
                else:
                    if info:
                        info['state'] = '감시중'
                        self.set_table_item(info['row'], 4, "👀 감시중", "#00b894")
                    self.log(f"⚠️ [{ticker}] 매수 체결 정보가 유효하지 않습니다(수량/금액 0). 상태를 감시중으로 복원합니다.")
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                if callable(release_reserved):
                    release_reserved(ticker)
                if callable(mark_reconciliation):
                    mark_reconciliation()
                schedule_twap = getattr(self, "_schedule_next_twap_buy_slice", None)
                if execution_mode == "twap_market" and callable(schedule_twap):
                    schedule_twap(ticker)
            elif state == 'cancel':
                if callable(transition_pending):
                    transition_pending(ticker, "cancel", reason="buy_execution_cancel")
                # 주문 취소됨
                info = self.universe.get(ticker)
                if info:
                    info['state'] = '감시중'
                    self.set_table_item(info['row'], 4, "👀 감시중", "#00b894")
                self.log(f"⚠️ [{ticker}] 매수 주문 취소됨")
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                if callable(release_reserved):
                    release_reserved(ticker)
                if callable(mark_reconciliation):
                    mark_reconciliation()
                schedule_twap = getattr(self, "_schedule_next_twap_buy_slice", None)
                if str((pending or {}).get("execution_mode", "")) == "twap_market" and callable(schedule_twap):
                    schedule_twap(ticker)
            else:
                # 아직 체결 안됨, 재시도 횟수 확인
                if retry_count < MAX_RETRIES:
                    QTimer.singleShot(
                        2000,
                        lambda t=ticker, u=uuid, rc=retry_count + 1, s=session_id: self.check_buy_execution(
                            t, u, rc, s
                        ),
                    )
                else:
                    self.log(f"[ERROR] [{ticker}] 매수 체결 확인 타임아웃 (60초)")
                    self.logger.error(f"매수 체결 확인 타임아웃: {ticker}, uuid={uuid}")
                    info = self.universe.get(ticker)
                    if info:
                        info['state'] = '체결확인실패'
                        self.set_table_item(info['row'], 4, "❓ 확인필요", "#ffc107")
                    if callable(resolve_timeout_pending):
                        resolved = resolve_timeout_pending(
                            ticker=ticker,
                            pending=pending,
                            reason="buy_execution_timeout",
                        )
                    else:
                        # Backward-compatible fallback for light test doubles.
                        if callable(clear_pending_if_uuid):
                            clear_pending_if_uuid(ticker, uuid)
                        else:
                            self.order_service.clear_pending(ticker)
                        if callable(release_reserved):
                            release_reserved(ticker)
                        resolved = True
                    if not resolved:
                        if callable(ops_alert):
                            ops_alert(
                                level="warning",
                                message=f"⚠️ [{ticker}] 매수 주문 타임아웃 unresolved - 수동검토 필요",
                                key=f"buy_timeout_unresolved:{uuid}",
                                cooldown=30,
                            )
        except Exception as e:
            if callable(register_manual_review):
                register_manual_review(
                    ticker=ticker,
                    uuid=uuid,
                    reason=f"buy_execution_exception:{e}",
                    order=None,
                )
            elif callable(clear_pending_if_uuid):
                clear_pending_if_uuid(ticker, uuid)
            else:
                self.order_service.clear_pending(ticker)
            if callable(release_reserved):
                release_reserved(ticker)
            self.logger.error(f"체결 확인 실패 ({ticker}): {e}")

    def execute_sell(self, ticker, reason):
        """매도 주문"""
        if not self.upbit and not self._is_paper_mode():
            return

        self._ensure_order_stability_state()
        if self.order_service.has_pending(ticker):
            pending = self.order_service.get_pending(ticker)
            self.log(f"[{ticker}] 중복 주문 방지: {pending['side']} 주문 대기 중")
            return
        
        info = self.universe.get(ticker)
        if not info:
            self.log(f"[WARN] {ticker} 보유 정보를 찾을 수 없어 매도를 건너뜁니다.")
            return

        qty = info['qty']
        if qty == 0:
            return
        session_id = getattr(self, "_active_session_id", 0)

        curr_price = float(info.get("current", 0.0) or 0.0)
        notional = float(qty) * curr_price if curr_price > 0 else float(info.get("invest_amt", 0.0) or 0.0)
        exec_cfg = self._get_execution_config()
        execution_plan = plan_execution(
            exec_cfg,
            notional,
            realized_vol_pct=0.0,
            force_mode=self._execution_mode(),
        )
        if execution_plan.mode == "twap_market":
            self.log(f"[{ticker}] 매도 TWAP는 현재 단일 시장가로 실행합니다.")
        
        try:
            ok, result, err_msg = self._place_sell_order(
                ticker,
                qty,
                side="SELL",
                session_id=session_id,
                source="auto_sell",
            )
            
            if ok and result and 'uuid' in result:
                if hasattr(self.order_service, "update_pending"):
                    self.order_service.update_pending(
                        ticker,
                        requested_qty=float(qty or 0.0),
                        sell_reason=str(reason or "매도"),
                        context_label="매도",
                        execution_mode="single_market" if execution_plan.mode == "twap_market" else str(execution_plan.mode),
                        expected_slippage_bps=float(execution_plan.expected_slippage_bps),
                        strategy_score=float(info.get("last_strategy_score", 0.0) or 0.0),
                        meta_score=float(info.get("last_meta_score", 0.0) or 0.0),
                        risk_state=str(info.get("last_risk_state", "normal")),
                    )
                info['state'] = '매도주문중'
                self.set_table_item(info['row'], 4, "⏳ 매도주문중", "#ffc107")
                self.log(f"📤 [{ticker}] 매도 주문: {qty:.8f} ({reason})")
                self.logger.info(f"매도 주문: {ticker} {qty:.8f} ({reason})")
                
                QTimer.singleShot(
                    2000,
                    lambda t=ticker, u=result['uuid'], r=reason, s=session_id: self.check_sell_execution(
                        t, u, r, retry_count=0, session_id=s
                    ),
                )
            else:
                self.log(f"[ERROR] 매도 주문 실패: {err_msg} / {result}")
                
        except Exception as e:
            self.order_service.clear_pending(ticker)
            self.log(f"[ERROR] 매도 주문 실패: {e}")
            self.logger.error(f"매도 주문 실패 ({ticker}): {e}")

    def _execute_partial_sell(self, ticker, qty, reason, level=None):
        """부분 매도 주문 (v2.7 신규 - 분할 익절용)"""
        if not self.upbit and not self._is_paper_mode():
            return False
        
        info = self.universe.get(ticker)
        if not info or qty <= 0:
            return False
        
        if self.order_service.has_pending(ticker):
            pending = self.order_service.get_pending(ticker)
            self.log(f"[{ticker}] 중복 주문 방지: {pending['side']} 주문 대기 중")
            return False

        curr_price = float(info.get("current", 0.0) or 0.0)
        notional = float(qty) * curr_price if curr_price > 0 else float(qty * info.get("buy_price", 0.0))
        exec_cfg = self._get_execution_config()
        execution_plan = plan_execution(
            exec_cfg,
            notional,
            realized_vol_pct=0.0,
            force_mode=self._execution_mode(),
        )
        if execution_plan.mode == "twap_market":
            self.log(f"[{ticker}] 분할익절 TWAP는 현재 단일 시장가로 실행합니다.")

        session_id = getattr(self, "_active_session_id", 0)
        try:
            ok, result, err_msg = self._place_sell_order(
                ticker,
                qty,
                side="PARTIAL_SELL",
                session_id=session_id,
                source="partial_sell",
            )
            
            if ok and result and 'uuid' in result:
                if hasattr(self.order_service, "update_pending"):
                    self.order_service.update_pending(
                        ticker,
                        requested_qty=float(qty or 0.0),
                        sell_reason=str(reason or "분할익절"),
                        partial_level=level,
                        context_label="분할 매도",
                        execution_mode="single_market" if execution_plan.mode == "twap_market" else str(execution_plan.mode),
                        expected_slippage_bps=float(execution_plan.expected_slippage_bps),
                        strategy_score=float(info.get("last_strategy_score", 0.0) or 0.0),
                        meta_score=float(info.get("last_meta_score", 0.0) or 0.0),
                        risk_state=str(info.get("last_risk_state", "normal")),
                    )
                self.log(f"📤 [{ticker}] 분할 매도: {qty:.8f} ({reason})")
                self.logger.info(f"분할 매도: {ticker} {qty:.8f} ({reason})")
                
                # 체결 확인 (분할 매도용)
                QTimer.singleShot(
                    2000,
                    lambda t=ticker, u=result['uuid'], q=qty, r=reason, lv=level, s=session_id: self._check_partial_sell_execution(
                        t, u, q, r, lv, retry_count=0, session_id=s
                    ),
                )
                return True
            else:
                self.log(f"[ERROR] 분할 매도 실패: {err_msg} / {result}")
                return False
                
        except Exception as e:
            self.order_service.clear_pending(ticker)
            self.log(f"[ERROR] 분할 매도 실패: {e}")
            self.logger.error(f"분할 매도 실패 ({ticker}): {e}")
            return False

    def _check_partial_sell_execution(self, ticker, uuid, qty, reason, level=None, retry_count=0, session_id=None):
        """분할 매도 체결 확인"""
        MAX_RETRIES = 30
        pending = self.order_service.get_pending(ticker)
        if not pending:
            return
        if pending and str(pending.get("uuid")) != str(uuid):
            return
        clear_pending_if_uuid = getattr(self.order_service, "clear_pending_if_uuid", None)
        mark_reconciliation = getattr(self, "_mark_reconciliation_dirty", None)

        try:
            if hasattr(self, "_safe_get_order"):
                order_raw = self._safe_get_order(uuid)
            else:
                order_raw = self.upbit.get_order(uuid)
            order = order_raw if isinstance(order_raw, dict) else None
            state = str(order.get("state", "")).lower() if order else "wait"
            if pending and hasattr(self.order_service, "update_pending"):
                self.order_service.update_pending(
                    ticker,
                    last_checked_at=datetime.datetime.now(),
                    retry_count=int(pending.get("retry_count", 0) or 0) + 1,
                )
                self._transition_pending(ticker, "wait", reason="partial_sell_execution_poll")

            if session_id is not None and session_id != getattr(self, "_active_session_id", 0):
                if state in ("done", "cancel"):
                    self._handle_session_mismatch_terminal(
                        ticker=ticker,
                        uuid=uuid,
                        side="PARTIAL_SELL",
                        state=state,
                        session_id=session_id,
                        source="_check_partial_sell_execution",
                    )
                return

            if state == 'done':
                self._transition_pending(ticker, "done", reason="partial_sell_execution_done")
                info = self.universe.get(ticker)
                if not info:
                    if callable(clear_pending_if_uuid):
                        clear_pending_if_uuid(ticker, uuid)
                    else:
                        self.order_service.clear_pending(ticker)
                    return

                executed_volume, _, trades_price = self.order_service.get_sell_fill_metrics(order)
                execution_mode = str((pending or {}).get("execution_mode", "single_market") or "single_market")
                expected_slippage_bps = float((pending or {}).get("expected_slippage_bps", 0.0) or 0.0)
                strategy_score = float((pending or {}).get("strategy_score", 0.0) or 0.0)
                meta_score = float((pending or {}).get("meta_score", 0.0) or 0.0)
                risk_state = str((pending or {}).get("risk_state", "normal") or "normal")

                if executed_volume <= 0 or trades_price <= 0:
                    self.log(f"⚠️ [{ticker}] 분할 매도 체결 정보가 유효하지 않습니다.")
                    if callable(clear_pending_if_uuid):
                        clear_pending_if_uuid(ticker, uuid)
                    else:
                        self.order_service.clear_pending(ticker)
                    return
                
                # 보유 수량 감소
                info['qty'] -= executed_volume
                if info['qty'] < 0:
                    info['qty'] = 0
                
                # 손익 계산 (부분)
                info['invest_amt'], profit = self.order_service.apply_partial_sell_accounting(
                    info['invest_amt'], info['qty'], executed_volume, trades_price
                )
                
                self.total_realized_profit += profit
                self.trade_count += 1
                if profit > 0:
                    self.win_count += 1
                
                # UI 업데이트
                self.lbl_total_profit.setText(f"📈 당일 실현손익: {self.total_realized_profit:,.0f}원")
                qty_item = info.get('ui_items', {}).get('qty')
                if qty_item is None:
                    qty_item = QTableWidgetItem("-")
                    self.table.setItem(info['row'], 5, qty_item)
                    info.setdefault('ui_items', {})['qty'] = qty_item
                qty_item.setText(f"{info['qty']:.8f}")
                
                self.log(f"✅ [{ticker}] 분할 매도 체결 (손익: {profit:+,.0f}원)")
                ref_price = float(info.get("current", trades_price) or trades_price)
                fee_krw = float(order.get("paid_fee", 0.0) or 0.0) if order else 0.0
                realized_slippage_bps = estimate_realized_slippage_bps(ref_price, trades_price, side="sell")
                self.add_trade_record(
                    ticker,
                    'PARTIAL_SELL',
                    trades_price,
                    executed_volume,
                    profit,
                    reason,
                    fee_krw=fee_krw,
                    expected_slippage_bps=expected_slippage_bps,
                    realized_slippage_bps=realized_slippage_bps,
                    execution_mode=execution_mode,
                    session_id=session_id,
                    risk_state=risk_state,
                    strategy_score=strategy_score,
                    meta_score=meta_score,
                )
                if level is not None and level not in info.setdefault('partial_sold', []):
                    info['partial_sold'].append(level)
                self._update_statistics()
                self._risk_snapshot_cache = {"ts": 0.0, "value": None}
                
                self.get_balance()
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                if callable(mark_reconciliation):
                    mark_reconciliation()
            elif state == 'cancel':
                self._transition_pending(ticker, "cancel", reason="partial_sell_execution_cancel")
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                self.log(f"⚠️ [{ticker}] 분할 매도 주문 취소됨")
                if callable(mark_reconciliation):
                    mark_reconciliation()
            else:
                if retry_count < MAX_RETRIES:
                    QTimer.singleShot(
                        2000,
                        lambda t=ticker, u=uuid, q=qty, r=reason, lv=level, rc=retry_count + 1, s=session_id: self._check_partial_sell_execution(
                            t, u, q, r, lv, rc, s
                        ),
                    )
                else:
                    self.log(f"[ERROR] [{ticker}] 분할 매도 체결 확인 타임아웃")
                    resolved = self._resolve_timeout_pending(
                        ticker=ticker,
                        pending=pending,
                        reason="partial_sell_execution_timeout",
                    )
                    if not resolved:
                        self._ops_alert(
                            level="warning",
                            message=f"⚠️ [{ticker}] 분할매도 타임아웃 unresolved - 수동검토 필요",
                            key=f"partial_timeout_unresolved:{uuid}",
                            cooldown=30,
                        )
        except Exception as e:
            self._register_manual_review(
                ticker=ticker,
                uuid=uuid,
                reason=f"partial_sell_execution_exception:{e}",
                order=None,
            )
            self.logger.error(f"분할 매도 체결 확인 실패 ({ticker}): {e}")

    def check_sell_execution(self, ticker, uuid, reason, retry_count=0, session_id=None):
        """매도 체결 확인 (최대 30회 재시도, 60초 타임아웃)"""
        MAX_RETRIES = 30  # 최대 30회 (60초)
        pending = self.order_service.get_pending(ticker)
        if not pending:
            return
        if pending and str(pending.get("uuid")) != str(uuid):
            return
        clear_pending_if_uuid = getattr(self.order_service, "clear_pending_if_uuid", None)
        mark_reconciliation = getattr(self, "_mark_reconciliation_dirty", None)
        transition_pending = getattr(self, "_transition_pending", None)
        handle_session_mismatch = getattr(self, "_handle_session_mismatch_terminal", None)
        resolve_timeout_pending = getattr(self, "_resolve_timeout_pending", None)
        ops_alert = getattr(self, "_ops_alert", None)
        register_manual_review = getattr(self, "_register_manual_review", None)
        persist_strategy_performance = getattr(self, "_persist_strategy_performance", None)

        try:
            if hasattr(self, "_safe_get_order"):
                order_raw = self._safe_get_order(uuid)
            else:
                order_raw = self.upbit.get_order(uuid)
            order = order_raw if isinstance(order_raw, dict) else None
            state = str(order.get("state", "")).lower() if order else "wait"
            if pending and hasattr(self.order_service, "update_pending"):
                self.order_service.update_pending(
                    ticker,
                    last_checked_at=datetime.datetime.now(),
                    retry_count=int(pending.get("retry_count", 0) or 0) + 1,
                )
                if callable(transition_pending):
                    transition_pending(ticker, "wait", reason="sell_execution_poll")

            if session_id is not None and session_id != getattr(self, "_active_session_id", 0):
                if state in ("done", "cancel"):
                    if callable(handle_session_mismatch):
                        handle_session_mismatch(
                            ticker=ticker,
                            uuid=uuid,
                            side="SELL",
                            state=state,
                            session_id=session_id,
                            source="check_sell_execution",
                        )
                return

            if state == 'done':
                if callable(transition_pending):
                    transition_pending(ticker, "done", reason="sell_execution_done")
                info = self.universe.get(ticker)
                if not info:
                    if callable(clear_pending_if_uuid):
                        clear_pending_if_uuid(ticker, uuid)
                    else:
                        self.order_service.clear_pending(ticker)
                    return

                executed_volume, sell_amount, trades_price = self.order_service.get_sell_fill_metrics(order)
                execution_mode = str((pending or {}).get("execution_mode", "single_market") or "single_market")
                expected_slippage_bps = float((pending or {}).get("expected_slippage_bps", 0.0) or 0.0)
                strategy_score = float((pending or {}).get("strategy_score", 0.0) or 0.0)
                meta_score = float((pending or {}).get("meta_score", 0.0) or 0.0)
                risk_state = str((pending or {}).get("risk_state", "normal") or "normal")

                if executed_volume <= 0 or sell_amount <= 0:
                    info['state'] = '보유중'
                    self.set_table_item(info['row'], 4, "💼 보유중", "#00b4d8")
                    self.log(f"⚠️ [{ticker}] 매도 체결 정보가 유효하지 않습니다.")
                    if callable(clear_pending_if_uuid):
                        clear_pending_if_uuid(ticker, uuid)
                    else:
                        self.order_service.clear_pending(ticker)
                    return
                
                # 손익 계산
                buy_amount = info['invest_amt']
                profit = sell_amount - buy_amount
                
                self.total_realized_profit += profit
                self.trade_count += 1
                if profit > 0:
                    self.win_count += 1
                
                # UI 업데이트
                profit_text = f"📈 당일 실현손익: {self.total_realized_profit:,.0f}원"
                self.lbl_total_profit.setText(profit_text)
                
                info['qty'] = 0
                info['state'] = '감시중'
                info['buy_price'] = 0
                info['invest_amt'] = 0
                info['high_since_buy'] = 0
                info['max_profit_rate'] = 0.0
                info['partial_sold'] = []
                self.set_table_item(info['row'], 4, "👀 감시중", "#00b894")
                qty_item = info.get('ui_items', {}).get('qty')
                if qty_item is not None:
                    qty_item.setText("0.00000000")
                buy_price_item = info.get('ui_items', {}).get('buy_price')
                if buy_price_item is not None:
                    buy_price_item.setText("-")
                invest_item = info.get('ui_items', {}).get('invest')
                if invest_item is not None:
                    invest_item.setText("-")
                profit_item = info.get('ui_items', {}).get('profit')
                if profit_item is not None:
                    profit_item.setText("-")
                max_profit_item = info.get('ui_items', {}).get('max_profit')
                if max_profit_item is not None:
                    max_profit_item.setText("-")

                if self.strategy:
                    self.strategy.update_consecutive_results(profit > 0)
                    self.strategy.clear_holding_start(ticker)
                    self.strategy.clear_partial_profit(ticker)
                    if hasattr(self, 'chk_use_cooldown') and self.chk_use_cooldown.isChecked():
                        cooldown_minutes = self.spin_cooldown.value() if hasattr(self, 'spin_cooldown') else None
                        self.strategy.set_cooldown(ticker, cooldown_minutes)
                
                fee_krw = float(order.get("paid_fee", 0.0) or 0.0) if order else 0.0
                realized_slippage_bps = estimate_realized_slippage_bps(float(info.get("current", trades_price) or trades_price), trades_price, side="sell")
                self.log(f"✅ [{ticker}] 매도 체결 (손익: {profit:+,.0f}원)")
                self.add_trade_record(
                    ticker,
                    'SELL',
                    trades_price,
                    executed_volume,
                    profit,
                    reason,
                    fee_krw=fee_krw,
                    expected_slippage_bps=expected_slippage_bps,
                    realized_slippage_bps=realized_slippage_bps,
                    execution_mode=execution_mode,
                    session_id=session_id,
                    risk_state=risk_state,
                    strategy_score=strategy_score,
                    meta_score=meta_score,
                )
                manager = getattr(self, "notification_manager", None)
                if manager is not None and EventType is not None and hasattr(manager, "notify_sell"):
                    try:
                        pnl_pct = (profit / buy_amount * 100.0) if buy_amount > 0 else 0.0
                        manager.notify_sell(ticker, trades_price, executed_volume, pnl_pct, reason=reason)
                    except Exception:
                        pass

                # 전략 성과 업데이트 (메타 시그널 용)
                strategy_id = str(info.get("last_strategy_id", "legacy") or "legacy")
                pnl_pct = (profit / buy_amount * 100.0) if buy_amount > 0 else 0.0
                tracker = getattr(self, "strategy_perf_tracker", None)
                if tracker is None:
                    tracker = StrategyPerformanceTracker()
                    self.strategy_perf_tracker = tracker
                tracker.update(strategy_id, pnl_pct)
                if callable(persist_strategy_performance):
                    persist_strategy_performance()
                
                self._update_statistics()
                self._risk_snapshot_cache = {"ts": 0.0, "value": None}
                self.get_balance()
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                if callable(mark_reconciliation):
                    mark_reconciliation()
            elif state == 'cancel':
                if callable(transition_pending):
                    transition_pending(ticker, "cancel", reason="sell_execution_cancel")
                self.log(f"⚠️ [{ticker}] 매도 주문 취소됨")
                info = self.universe.get(ticker)
                if info and info['qty'] > 0:
                    info['state'] = '보유중'
                    self.set_table_item(info['row'], 4, "💼 보유중", "#00b4d8")
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                if callable(mark_reconciliation):
                    mark_reconciliation()
            else:
                if retry_count < MAX_RETRIES:
                    QTimer.singleShot(
                        2000,
                        lambda t=ticker, u=uuid, r=reason, rc=retry_count + 1, s=session_id: self.check_sell_execution(
                            t, u, r, rc, s
                        ),
                    )
                else:
                    self.log(f"[ERROR] [{ticker}] 매도 체결 확인 타임아웃 (60초)")
                    self.logger.error(f"매도 체결 확인 타임아웃: {ticker}, uuid={uuid}")
                    info = self.universe.get(ticker)
                    if info:
                        info['state'] = '체결확인실패'
                        self.set_table_item(info['row'], 4, "❓ 확인필요", "#ffc107")
                    if callable(resolve_timeout_pending):
                        resolved = resolve_timeout_pending(
                            ticker=ticker,
                            pending=pending,
                            reason="sell_execution_timeout",
                        )
                    else:
                        if callable(clear_pending_if_uuid):
                            clear_pending_if_uuid(ticker, uuid)
                        else:
                            self.order_service.clear_pending(ticker)
                        resolved = True
                    if not resolved:
                        if callable(ops_alert):
                            ops_alert(
                                level="warning",
                                message=f"⚠️ [{ticker}] 매도 주문 타임아웃 unresolved - 수동검토 필요",
                                key=f"sell_timeout_unresolved:{uuid}",
                                cooldown=30,
                            )
        except Exception as e:
            if callable(register_manual_review):
                register_manual_review(
                    ticker=ticker,
                    uuid=uuid,
                    reason=f"sell_execution_exception:{e}",
                    order=None,
                )
            elif callable(clear_pending_if_uuid):
                clear_pending_if_uuid(ticker, uuid)
            else:
                self.order_service.clear_pending(ticker)
            self.logger.error(f"매도 체결 확인 실패 ({ticker}): {e}")

    # ------------------------------------------------------------------
    # 일괄 매도/매수 기능 (v2.6 신규)
    # ------------------------------------------------------------------

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
        """리스크 한도 체크"""
        _risk_ops.bind_runtime(
            Config=Config,
            RiskLimitConfig=RiskLimitConfig,
            build_portfolio_risk_snapshot=build_portfolio_risk_snapshot,
            evaluate_risk_limits=evaluate_risk_limits,
            pyupbit=pyupbit,
            time=time,
        )
        return _risk_ops.check_risk_limits(self)

    # ------------------------------------------------------------------
    # 운영/수동검토 큐
    # ------------------------------------------------------------------

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
        """프리셋 적용"""
        if preset_type in Config.DEFAULT_PRESETS:
            preset = Config.DEFAULT_PRESETS[preset_type]
            self.apply_preset_values(preset)

    def set_table_item(self, row, col, text, bg_color):
        """테이블 아이템 설정"""
        item = self.table.item(row, col)
        if item is None:
            item = QTableWidgetItem(text)
            self.table.setItem(row, col, item)
        else:
            item.setText(text)
        item.setBackground(QColor(bg_color))
        item.setForeground(QColor("#1a1a2e"))

    def _update_statistics(self):
        """통계 업데이트"""
        self.stat_trades.setText(f"📊 총 거래 횟수\n{self.trade_count} 회")
        
        winrate = (self.win_count / self.trade_count * 100) if self.trade_count > 0 else 0
        self.stat_winrate.setText(f"🎯 승률\n{winrate:.1f} %")
        
        self.stat_profit.setText(f"💰 총 실현손익\n{self.total_realized_profit:,.0f} 원")
        holdings = int(self._get_risk_snapshot(force=False).get("holdings_count", 0) or 0)
        self.stat_holdings.setText(f"📦 보유 종목\n{holdings} 개")

    def reset_statistics(self):
        """통계 초기화"""
        reply = QMessageBox.question(self, "확인", "거래 통계를 초기화하시겠습니까?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.total_realized_profit = 0
            self.trade_count = 0
            self.win_count = 0
            self._update_statistics()
            self.lbl_total_profit.setText("📈 당일 실현손익: 0 원")
            self.log("🔄 통계 초기화됨")

    def log(self, msg):
        """로그 출력 (v2.5 메모리 제한 적용)"""
        t = datetime.datetime.now().strftime("[%H:%M:%S]")
        self.log_text.append(f"{t} {msg}")

        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())
    
    # ------------------------------------------------------------------
    # v2.7: 도구 메뉴 함수
    # ------------------------------------------------------------------



