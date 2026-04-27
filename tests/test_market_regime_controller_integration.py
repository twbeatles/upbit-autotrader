import json
import types
from pathlib import Path
from typing import Any

from upbit_autotrader.controllers.history_controller import TraderHistoryController
from upbit_autotrader.controllers.settings_field_specs import (
    COMMON_FIELD_SPECS,
    apply_settings_to_widgets,
    collect_settings_from_specs,
)
from upbit_autotrader.controllers.trading_controller import TraderTradingController
from upbit_autotrader.core.config import Config
from upbit_autotrader.execution.execution_model import ExecutionConfig
from upbit_autotrader.market_regime.engine import MarketRegimeOutput
from upbit_autotrader.services.order_service import UpbitOrderService


class _Check:
    def __init__(self, checked=False):
        self._checked = bool(checked)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        self._checked = bool(checked)


class _Spin:
    def __init__(self, value: float = 0):
        self._value = value

    def value(self):
        return self._value

    def setValue(self, value):
        self._value = value


class _Combo:
    def __init__(self, text):
        self._text = text

    def currentText(self):
        return self._text


class _Logger:
    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None


class _Table:
    def setItem(self, *args, **kwargs):
        return None


class _OrderApi:
    def __init__(self, order_map):
        self.order_map = order_map

    def get_order(self, uuid):
        return self.order_map.get(uuid, {"state": "wait"})


def test_market_regime_filter_blocks_buy_before_execute():
    class _Trader(TraderTradingController):
        def __init__(self):
            self.strategy = None
            self.combo_candle = _Combo(Config.DEFAULT_CANDLE)
            self.chk_use_rsi = _Check(False)
            self.chk_use_volume = _Check(False)
            self.chk_use_entry_scoring = _Check(False)
            self.chk_use_market_regime_filter = _Check(True)
            self.chk_use_market_regime_risk_scaling = _Check(False)
            self.chk_market_regime_use_fear_greed = _Check(True)
            self.chk_market_regime_use_etf_flow = _Check(False)
            self.spin_market_regime_min_score = _Spin(55.0)
            self.spin_market_regime_refresh_sec = _Spin(60)
            self.spin_market_regime_top_n = _Spin(20)
            self.market_regime_output = MarketRegimeOutput(40.0, 0.5, "defensive")
            self.market_regime_snapshot = types.SimpleNamespace(as_of="2026-03-25T00:00:00+00:00")
            self.logs = []
            self.buy_calls = []

        def _get_strategy_runtime_config(self):
            return None

        def _use_meta_signal(self):
            return False

        def check_risk_limits(self):
            return True

        def execute_buy(self, ticker, curr_price):
            self.buy_calls.append((ticker, curr_price))

        def log(self, msg):
            self.logs.append(msg)

    trader = _Trader()
    info = {"target": 100.0, "ma5": 90.0}

    trader._check_buy_condition("KRW-BTC", 120.0, info)

    assert trader.buy_calls == []
    assert info["last_market_regime_score"] == 40.0
    assert any("market regime" in message for message in trader.logs)


def test_execute_buy_applies_market_regime_risk_scaling_before_execution(monkeypatch):
    class _Trader(TraderTradingController):
        def __init__(self):
            self.upbit = object()
            self.order_service = UpbitOrderService()
            self.universe = {"KRW-BTC": {"row": 0, "state": "감시중", "qty": 0.0}}
            self.strategy = None
            self.spin_betting = _Spin(10.0)
            self.combo_candle = _Combo(Config.DEFAULT_CANDLE)
            self.chk_use_market_regime_filter = _Check(False)
            self.chk_use_market_regime_risk_scaling = _Check(True)
            self.chk_market_regime_use_fear_greed = _Check(True)
            self.chk_market_regime_use_etf_flow = _Check(False)
            self.spin_market_regime_min_score = _Spin(55.0)
            self.spin_market_regime_refresh_sec = _Spin(60)
            self.spin_market_regime_top_n = _Spin(20)
            self.market_regime_output = MarketRegimeOutput(35.0, 0.5, "defensive")
            self.market_regime_snapshot = types.SimpleNamespace(as_of="2026-03-25T00:00:00+00:00")
            self.logger = _Logger()
            self.placed_amounts = []
            self.logs = []
            self._active_session_id = 7

        def _ensure_order_stability_state(self):
            return None

        def _is_paper_mode(self):
            return False

        def _get_strategy_runtime_config(self):
            return None

        def _use_risk_budget_sizing(self):
            return False

        def _get_available_krw(self):
            return 100000.0

        def _get_execution_config(self):
            return ExecutionConfig(enabled=False)

        def _execution_mode(self):
            return "single_market"

        def _reserve_krw_for_buy(self, ticker, amount, session_id=0):
            return True

        def _release_reserved_krw(self, ticker):
            return None

        def _place_buy_order(self, ticker, amount, session_id=0, source="auto_buy"):
            self.placed_amounts.append(float(amount))
            self.order_service.mark_pending(ticker, "BUY", "buy-1", session_id=session_id, source=source)
            return True, {"uuid": "buy-1"}, ""

        def set_table_item(self, row, col, text, bg_color):
            return None

        def log(self, msg):
            self.logs.append(msg)

    monkeypatch.setattr(
        "upbit_autotrader.controllers.trading_controller.QTimer.singleShot",
        lambda _ms, _cb: None,
    )
    trader = _Trader()

    trader.execute_buy("KRW-BTC", 50000000.0)

    assert trader.placed_amounts == [5000.0]
    pending = trader.order_service.get_pending("KRW-BTC")
    assert pending is not None
    assert pending["market_regime_score"] == 35.0
    assert pending["market_regime_label"] == "defensive"


def test_market_regime_wrapper_returns_neutral_startup_fallback():
    trader = TraderTradingController.__new__(TraderTradingController)

    out = trader._get_market_regime_output()

    assert out.market_regime_score == 50.0
    assert out.label == "neutral"
    assert out.risk_multiplier == 1.0


def test_trade_history_serializes_market_regime_extra_fields(monkeypatch):
    class _History(TraderHistoryController):
        def __init__(self):
            self.trade_history = []
            self.logger = _Logger()

        def _schedule_trade_history_save(self):
            return None

    history_path = Path(".pytest_trade_history_market_regime.json")
    if history_path.exists():
        history_path.unlink()
    monkeypatch.setattr(Config, "TRADE_HISTORY_FILE", str(history_path))
    history = _History()

    history.add_trade_record(
        "KRW-BTC",
        "BUY",
        100.0,
        1.0,
        reason="market_regime_test",
        market_regime_score=58.0,
        market_regime_label="risk_on",
        market_regime_ts="2026-03-25T00:00:00+00:00",
    )
    history._save_trade_history_now()

    payload = json.loads(history_path.read_text(encoding="utf-8"))
    assert payload[0]["market_regime_score"] == 58.0
    assert payload[0]["market_regime_label"] == "risk_on"
    assert payload[0]["market_regime_ts"] == "2026-03-25T00:00:00+00:00"
    history_path.unlink()


def test_market_regime_settings_round_trip_uses_field_specs():
    target_keys = {
        "use_market_regime_filter",
        "use_market_regime_risk_scaling",
        "market_regime_min_score",
        "market_regime_refresh_sec",
        "market_regime_top_n",
        "market_regime_use_fear_greed",
        "market_regime_use_etf_flow",
    }
    specs = tuple(spec for spec in COMMON_FIELD_SPECS if spec.key in target_keys)

    class _SettingsHolder:
        pass

    holder = _SettingsHolder()
    for spec in specs:
        if spec.kind == "check":
            setattr(holder, spec.attr, _Check(False))
        else:
            setattr(holder, spec.attr, _Spin(0))

    expected = {
        "use_market_regime_filter": True,
        "use_market_regime_risk_scaling": True,
        "market_regime_min_score": 61.5,
        "market_regime_refresh_sec": 90,
        "market_regime_top_n": 15,
        "market_regime_use_fear_greed": False,
        "market_regime_use_etf_flow": True,
    }

    apply_settings_to_widgets(holder, expected, Config, specs=specs)
    actual = collect_settings_from_specs(holder, Config, specs=specs)

    assert actual == expected


def test_check_buy_execution_records_market_regime_fields():
    class _Trader(TraderTradingController):
        def __init__(self):
            self.upbit = _OrderApi(
                {
                    "buy-1": {
                        "state": "done",
                        "executed_volume": "0.01",
                        "paid_fee": "10",
                        "trades": [{"price": "50000000", "volume": "0.01"}],
                    }
                }
            )
            self.order_service = UpbitOrderService()
            self.universe = {
                "KRW-BTC": {"row": 0, "state": "주문중", "qty": 0.0, "buy_price": 0.0, "invest_amt": 0.0, "ui_items": {}}
            }
            self.table = _Table()
            self.logger = _Logger()
            self.strategy = None
            self.trade_records = []

        def set_table_item(self, row, col, text, bg_color):
            return None

        def log(self, *_args, **_kwargs):
            return None

        def add_trade_record(self, *args, **kwargs):
            self.trade_records.append(kwargs)

        def get_balance(self):
            return None

    trader = _Trader()
    trader.order_service.mark_pending("KRW-BTC", "BUY", "buy-1")
    trader.order_service.update_pending(
        "KRW-BTC",
        market_regime_score=64.0,
        market_regime_label="risk_on",
        market_regime_ts="2026-03-25T00:00:00+00:00",
    )

    trader.check_buy_execution("KRW-BTC", "buy-1")

    assert trader.trade_records[0]["market_regime_score"] == 64.0
    assert trader.trade_records[0]["market_regime_label"] == "risk_on"
    assert trader.trade_records[0]["market_regime_ts"] == "2026-03-25T00:00:00+00:00"
