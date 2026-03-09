import datetime
from unittest.mock import patch

from PyQt6.QtWidgets import QMessageBox

from upbit_autotrader.core.config import Config
from upbit_autotrader.controllers.batch_controller import TraderBatchController
from upbit_autotrader.controllers.settings_controller import TraderSettingsController
from upbit_autotrader.controllers.trading_controller import TraderTradingController
from upbit_autotrader.services.order_service import UpbitOrderService


class _DummyLogger:
    def info(self, *_args, **_kwargs):
        return None

    def warning(self, *_args, **_kwargs):
        return None

    def error(self, *_args, **_kwargs):
        return None


class _Label:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text

    def setStyleSheet(self, *_):
        return None


class _Text:
    def __init__(self, value=""):
        self._value = value

    def text(self):
        return self._value

    def setText(self, value):
        self._value = value


class _Combo:
    def __init__(self, text):
        self._text = text

    def currentText(self):
        return self._text

    def setCurrentText(self, text):
        self._text = text


class _Check:
    def __init__(self, checked=False):
        self._checked = bool(checked)

    def isChecked(self):
        return bool(self._checked)

    def setChecked(self, checked):
        self._checked = bool(checked)


class _Spin:
    def __init__(self, value=0.0):
        self._value = value

    def value(self):
        return self._value

    def setValue(self, value):
        self._value = value


class _Button:
    def setEnabled(self, *_):
        return None


class _Table:
    def __init__(self):
        self._rows = 0
        self._items = {}
        self._current_row = -1

    def setRowCount(self, count):
        self._rows = int(count)
        self._items = {k: v for k, v in self._items.items() if k[0] < self._rows}

    def rowCount(self):
        return int(self._rows)

    def insertRow(self, row):
        self._rows = max(self._rows, int(row) + 1)

    def setItem(self, row, col, item):
        self._items[(int(row), int(col))] = item

    def item(self, row, col):
        return self._items.get((int(row), int(col)))

    def setUpdatesEnabled(self, *_):
        return None

    def currentRow(self):
        return int(self._current_row)

    def setCurrentRow(self, row):
        self._current_row = int(row)


class _UpbitOrderMap:
    def __init__(self, order_map=None):
        self.order_map = dict(order_map or {})
        self.buy_calls = []

    def get_order(self, uuid):
        return self.order_map.get(uuid, {"state": "wait"})

    def cancel_order(self, _uuid):
        return {"state": "cancel"}

    def buy_market_order(self, ticker, amount):
        self.buy_calls.append((ticker, amount))
        return {"uuid": f"buy-{len(self.buy_calls)}"}


def test_check_sell_execution_done_cancel_no_manual_review_side_effect():
    class _Trader(TraderTradingController):
        def __init__(self, order_map):
            self.upbit = _UpbitOrderMap(order_map)
            self.order_service = UpbitOrderService()
            self.pending_orders = self.order_service.pending_orders
            self.universe = {
                "KRW-BTC": {
                    "row": 0,
                    "state": "매도주문중",
                    "qty": 1.0,
                    "invest_amt": 10_000.0,
                    "current": 12_000.0,
                    "ui_items": {},
                }
            }
            self.total_realized_profit = 0.0
            self.trade_count = 0
            self.win_count = 0
            self.strategy = None
            self.logger = _DummyLogger()
            self.manual_review_calls = 0
            self.lbl_total_profit = _Label()

        def _register_manual_review(self, *_args, **_kwargs):
            self.manual_review_calls += 1

        def set_table_item(self, *_args, **_kwargs):
            return None

        def log(self, *_args, **_kwargs):
            return None

        def add_trade_record(self, *_args, **_kwargs):
            return None

        def _update_statistics(self):
            return None

        def get_balance(self):
            return None

    done = _Trader(
        {
            "sell-done": {
                "state": "done",
                "executed_volume": "1",
                "executed_funds": "12000",
                "paid_fee": "10",
                "trades": [],
            }
        }
    )
    done.order_service.mark_pending("KRW-BTC", "SELL", "sell-done")
    done.check_sell_execution("KRW-BTC", "sell-done", "테스트")
    assert not done.order_service.has_pending("KRW-BTC")
    assert done.manual_review_calls == 0

    cancel = _Trader({"sell-cancel": {"state": "cancel"}})
    cancel.order_service.mark_pending("KRW-BTC", "SELL", "sell-cancel")
    cancel.check_sell_execution("KRW-BTC", "sell-cancel", "테스트")
    assert not cancel.order_service.has_pending("KRW-BTC")
    assert cancel.manual_review_calls == 0


def test_check_partial_sell_execution_done_cancel_no_nameerror_path():
    class _Trader(TraderTradingController):
        def __init__(self, order_map):
            self.upbit = _UpbitOrderMap(order_map)
            self.order_service = UpbitOrderService()
            self.pending_orders = self.order_service.pending_orders
            self.universe = {
                "KRW-ETH": {
                    "row": 0,
                    "state": "보유중",
                    "qty": 1.0,
                    "invest_amt": 10_000.0,
                    "current": 12_000.0,
                    "ui_items": {},
                    "partial_sold": [],
                }
            }
            self.table = _Table()
            self.lbl_total_profit = _Label()
            self.total_realized_profit = 0.0
            self.trade_count = 0
            self.win_count = 0
            self.logger = _DummyLogger()
            self.manual_review_calls = 0
            self._risk_snapshot_cache = {"ts": 0.0, "value": None}

        def _register_manual_review(self, *_args, **_kwargs):
            self.manual_review_calls += 1

        def log(self, *_args, **_kwargs):
            return None

        def add_trade_record(self, *_args, **_kwargs):
            return None

        def _update_statistics(self):
            return None

        def get_balance(self):
            return None

    done = _Trader(
        {
            "partial-done": {
                "state": "done",
                "executed_volume": "0.5",
                "executed_funds": "6000",
                "paid_fee": "6",
                "trades": [],
            }
        }
    )
    done.order_service.mark_pending("KRW-ETH", "PARTIAL_SELL", "partial-done")
    done._check_partial_sell_execution("KRW-ETH", "partial-done", qty=0.5, reason="테스트")
    assert not done.order_service.has_pending("KRW-ETH")
    assert done.manual_review_calls == 0

    cancel = _Trader({"partial-cancel": {"state": "cancel"}})
    cancel.order_service.mark_pending("KRW-ETH", "PARTIAL_SELL", "partial-cancel")
    cancel._check_partial_sell_execution("KRW-ETH", "partial-cancel", qty=0.5, reason="테스트")
    assert not cancel.order_service.has_pending("KRW-ETH")
    assert cancel.manual_review_calls == 0


def test_start_trading_paper_balance_zero_keeps_stopped_and_no_session_increment():
    class _Trader(TraderTradingController):
        def __init__(self):
            self.upbit = None
            self.is_connected = False
            self.input_coins = _Text("KRW-BTC")
            self.combo_candle = _Combo(Config.DEFAULT_CANDLE)
            self.table = _Table()
            self.btn_start = _Button()
            self.btn_stop = _Button()
            self.status_trading = _Label()
            self.status_realtime = _Label()
            self.strategy = None
            self.logger = _DummyLogger()
            self.order_service = UpbitOrderService()
            self.pending_orders = self.order_service.pending_orders
            self.universe = {}
            self.is_running = False
            self.daily_loss_triggered = False
            self._active_session_id = 0
            self.balance = 0.0
            self.initial_balance = 0.0

        def _is_paper_mode(self):
            return True

        def _allow_paper_without_login(self):
            return True

        def _enable_account_wide_sync(self):
            return False

        def _seed_paper_balance_once(self):
            return None

        def get_balance(self):
            self.balance = 0.0

        def log(self, *_args, **_kwargs):
            return None

    trader = _Trader()
    with patch("upbit_autotrader.controllers.trading_controller.QMessageBox.warning"):
        trader.start_trading()
    assert trader.is_running is False
    assert trader._active_session_id == 0


def test_sync_account_holdings_initializes_external_row_columns():
    class _Trader(TraderTradingController):
        def __init__(self):
            self.order_service = UpbitOrderService()
            self.pending_orders = self.order_service.pending_orders
            self.universe = {}
            self.table = _Table()
            self.logger = _DummyLogger()
            self._risk_snapshot_cache = {"ts": 0.0, "value": None}

        def set_table_item(self, row, col, text, bg_color):
            from PyQt6.QtWidgets import QTableWidgetItem

            item = self.table.item(row, col)
            if item is None:
                item = QTableWidgetItem(text)
                self.table.setItem(row, col, item)
            else:
                item.setText(text)

    trader = _Trader()
    trader._sync_account_holdings_to_universe(
        account_holdings=[
            {
                "ticker": "KRW-XRP",
                "qty": 12.0,
                "buy_price": 1000.0,
                "current_price": 1100.0,
                "value": 13200.0,
            }
        ],
        include_external=True,
    )
    info = trader.universe["KRW-XRP"]
    assert trader.table.item(info["row"], 5) is not None
    assert trader.table.item(info["row"], 6) is not None
    assert trader.table.item(info["row"], 9) is not None
    qty_item = trader.table.item(info["row"], 5)
    assert qty_item is not None
    assert qty_item.text() == "12.00000000"


def test_reconcile_pending_promotes_stale_missing_order_to_manual_review_even_without_force():
    class _Trader(TraderTradingController):
        def __init__(self):
            self.upbit = object()
            self.order_service = UpbitOrderService()
            self.pending_orders = self.order_service.pending_orders
            self.logger = _DummyLogger()
            self.chk_manual_review_on_timeout = _Check(True)
            self.chk_paper_trading = _Check(False)
            self._manual_review_queue = {}

        def _safe_get_order(self, uuid):
            return None

        def _api_cancel_order(self, uuid):
            return None

        def _sync_account_holdings_to_universe(self, *args, **kwargs):
            return None

        def log(self, *_args, **_kwargs):
            return None

    trader = _Trader()
    trader.order_service.mark_pending("KRW-BTC", "BUY", "u-missing")
    trader.order_service.update_pending(
        "KRW-BTC",
        requested_at=datetime.datetime.now() - datetime.timedelta(seconds=Config.PENDING_STALE_TIMEOUT_SEC + 1),
        missing_order_count=int(Config.API_MAX_RETRIES),
    )
    trader._reconcile_pending_orders(force=False)

    pending = trader.order_service.get_pending("KRW-BTC")
    assert pending is not None
    assert pending.get("lifecycle_state") == "manual_review"
    assert trader._manual_review_queue


def test_risk_snapshot_prefers_account_wide_latest_same_ticker_data():
    class _Trader(TraderTradingController):
        def __init__(self):
            self.order_service = UpbitOrderService()
            self.pending_orders = self.order_service.pending_orders
            self.universe = {
                "KRW-BTC": {
                    "qty": 1.0,
                    "buy_price": 100.0,
                    "current": 110.0,
                }
            }
            self.total_realized_profit = 0.0
            self.initial_balance = 1_000_000.0
            self._risk_snapshot_cache = {"ts": 0.0, "value": None}
            self.chk_risk_include_unrealized = _Check(True)
            self.chk_risk_include_external_holdings = _Check(True)
            self.logger = _DummyLogger()

        def get_account_holdings(self):
            return [
                {
                    "ticker": "KRW-BTC",
                    "qty": 2.0,
                    "buy_price": 200.0,
                    "current_price": 250.0,
                    "value": 500.0,
                }
            ]

        def log(self, *_args, **_kwargs):
            return None

    snapshot = _Trader()._get_risk_snapshot(force=True)
    assert snapshot["unrealized_pnl"] == 100.0


def test_correlation_history_targets_notional_top_n_positions():
    class _Series(list):
        def tolist(self):
            return list(self)

    class _FakeDf:
        def __init__(self, count):
            self._close = _Series([1.0 + (i * 0.001) for i in range(int(count))])

        def __len__(self):
            return len(self._close)

        def __getitem__(self, key):
            if key == "close":
                return self._close
            raise KeyError(key)

    class _FakePyupbit:
        def __init__(self):
            self.calls = []

        def get_ohlcv(self, ticker, interval=None, count=0):
            self.calls.append((ticker, interval, count))
            return _FakeDf(count)

    class _Trader(TraderTradingController):
        def __init__(self):
            self.order_service = UpbitOrderService()
            self.pending_orders = self.order_service.pending_orders
            self.universe = {}
            self.total_realized_profit = 0.0
            self.initial_balance = 1_000_000.0
            self._risk_snapshot_cache = {"ts": 0.0, "value": None}
            self.chk_risk_include_unrealized = _Check(True)
            self.chk_risk_include_external_holdings = _Check(True)
            self.spin_max_correlation_exposure_pct = _Spin(50.0)
            self.combo_candle = _Combo(Config.DEFAULT_CANDLE)
            self.logger = _DummyLogger()

        def get_account_holdings(self):
            rows = []
            for idx in range(25):
                rows.append(
                    {
                        "ticker": f"KRW-T{idx:02d}",
                        "qty": float(idx + 1),
                        "buy_price": 1000.0,
                        "current_price": 1000.0,
                        "value": float(idx + 1) * 1000.0,
                    }
                )
            return rows

        def log(self, *_args, **_kwargs):
            return None

    fake = _FakePyupbit()
    trader = _Trader()
    with patch("upbit_autotrader.controllers.trading_controller.pyupbit", fake):
        trader._get_risk_snapshot(force=True)

    assert len(fake.calls) == int(Config.DEFAULT_CORRELATION_MAX_TICKERS)
    called = [row[0] for row in fake.calls]
    assert called[0] == "KRW-T24"
    expected = {f"KRW-T{idx:02d}" for idx in range(5, 25)}
    assert set(called) == expected


def test_execute_batch_buy_stops_when_risk_limit_blocks():
    class _Trader(TraderBatchController):
        def __init__(self):
            self.upbit = _UpbitOrderMap()
            self.order_service = UpbitOrderService()
            self.input_coins = _Text("KRW-BTC,KRW-ETH")
            self.balance = 1_000_000.0
            self._reserved_krw_by_ticker = {}
            self._active_session_id = 1
            self.universe = {}
            self.table = _Table()
            self.chk_auto_start_after_batch = _Check(False)
            self.logs = []

        def check_risk_limits(self):
            return False

        def _ensure_order_stability_state(self):
            return None

        def log(self, msg):
            self.logs.append(msg)

        def get_balance(self):
            return None

        def start_trading(self):
            return None

        def set_table_item(self, *_args, **_kwargs):
            return None

    trader = _Trader()
    with patch("upbit_autotrader.controllers.batch_controller.QMessageBox.warning"):
        trader.execute_batch_buy()
    assert trader.upbit.buy_calls == []
    assert any("리스크 한도" in msg for msg in trader.logs)


def test_settings_load_preserves_meta_score_threshold_precision():
    class _Trader(TraderSettingsController):
        def __init__(self):
            self.input_coins = _Text()
            self.combo_candle = _Combo(Config.DEFAULT_CANDLE)
            self.spin_betting = _Spin(0.0)
            self.spin_k = _Spin(0.0)
            self.spin_ts_start = _Spin(0.0)
            self.spin_ts_stop = _Spin(0.0)
            self.spin_loss = _Spin(0.0)
            self.chk_use_rsi = _Check(False)
            self.spin_rsi_upper = _Spin(0.0)
            self.spin_rsi_period = _Spin(0.0)
            self.chk_use_volume = _Check(False)
            self.spin_volume_mult = _Spin(0.0)
            self.chk_use_risk = _Check(False)
            self.spin_max_loss = _Spin(0.0)
            self.spin_max_holdings = _Spin(0.0)
            self.chk_use_partial_tp = _Check(False)
            self.chk_use_entry_scoring = _Check(False)
            self.spin_entry_score_threshold = _Spin(0.0)
            self.spin_meta_score_threshold = _Spin(0.0)
            self.input_access = _Text()
            self.input_secret = _Text()
            self.system_settings = {}
            self.advanced_settings = {
                "use_cooldown": False,
                "cooldown_minutes": 30,
                "use_time_exit": False,
                "max_holding_hours": 24,
                "use_dynamic_position": False,
                "use_mtf": False,
                "use_gap_analysis": False,
                "use_breakout_confirm": False,
                "breakout_confirm_ticks": 3,
            }
            self.logger = _DummyLogger()
            self._logs = []

        def configure_runtime_integrations(self):
            return None

        def refresh_trade_action_buttons(self):
            return None

        def send_notification(self, *_args, **_kwargs):
            return None

        def log(self, msg):
            self._logs.append(msg)

    trader = _Trader()
    with patch(
        "upbit_autotrader.controllers.settings_controller.load_settings_v2",
        return_value={"meta_score_threshold": 60.75},
    ):
        trader.load_settings()
    assert abs(float(trader.spin_meta_score_threshold.value()) - 60.75) < 1e-9


def test_manual_review_resolve_removes_queue_only_and_keeps_pending():
    class _Trader(TraderTradingController):
        def __init__(self):
            self.order_service = UpbitOrderService()
            self.pending_orders = self.order_service.pending_orders
            self.logger = _DummyLogger()
            self.manual_review_table = _Table()
            self.manual_review_table.setCurrentRow(0)
            self.lbl_manual_review_count = _Label()
            self._manual_review_row_keys = ["q1"]
            self._manual_review_queue = {
                "q1": {
                    "ticker": "KRW-BTC",
                    "uuid": "u1",
                    "reason": "test",
                    "queued_at": datetime.datetime.now().isoformat(),
                    "pending": {"lifecycle_state": "manual_review", "session_id": 1},
                }
            }

        def log(self, *_args, **_kwargs):
            return None

    trader = _Trader()
    trader.order_service.mark_pending("KRW-BTC", "BUY", "u1", session_id=1)
    trader.order_service.update_pending("KRW-BTC", lifecycle_state="manual_review")
    trader.resolve_selected_manual_review()
    assert "q1" not in trader._manual_review_queue
    assert trader.order_service.has_pending("KRW-BTC")
