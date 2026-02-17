from unittest.mock import patch

from PyQt6.QtWidgets import QMessageBox

from upbit_config import Config
from upbit_order_service import UpbitOrderService
from upbit_trader_batch_controller import TraderBatchController
from upbit_trader_settings_controller import TraderSettingsController
from upbit_trader_trading_controller import TraderTradingController


class _DummyLogger:
    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None


class _Text:
    def __init__(self, value):
        self._value = value

    def text(self):
        return self._value


class _Combo:
    def __init__(self, text):
        self._text = text

    def currentText(self):
        return self._text


class _Button:
    def setEnabled(self, *_):
        return None


class _Label:
    def __init__(self):
        self.value = ""

    def setText(self, value):
        self.value = value

    def setStyleSheet(self, *_):
        return None


class _Spin:
    def __init__(self, value):
        self._value = value

    def value(self):
        return self._value


class _Check:
    def __init__(self, checked):
        self._checked = checked

    def isChecked(self):
        return self._checked


class _DummyThread:
    def __init__(self):
        self.coins = []

    def set_coins(self, coins):
        self.coins = list(coins)

    def start(self):
        return None

    def isRunning(self):
        return False


class _DummyTable:
    def __init__(self):
        self._rows = 0
        self._items = {}

    def setRowCount(self, count):
        self._rows = count

    def insertRow(self, row):
        self._rows = max(self._rows, row + 1)

    def setItem(self, row, col, item):
        self._items[(row, col)] = item

    def item(self, row, col):
        return self._items.get((row, col))

    def setUpdatesEnabled(self, *_):
        return None


class _FakeOrderApi:
    def __init__(self, order_map=None):
        self.order_map = order_map or {}
        self.buy_calls = []

    def get_order(self, uuid):
        return self.order_map.get(uuid, {"state": "wait"})

    def buy_market_order(self, ticker, amount):
        self.buy_calls.append((ticker, amount))
        return {"uuid": f"buy-{len(self.buy_calls)}"}


def test_send_notification_does_not_raise_when_tray_unavailable():
    class _NotifyTrader(TraderSettingsController):
        def __init__(self):
            self.system_settings = {"show_tray_notifications": True}
            self.logger = _DummyLogger()

    trader = _NotifyTrader()
    trader.send_notification("title", "message")


def test_start_trading_does_not_clear_existing_pending_orders():
    class _StartTrader(TraderTradingController):
        def __init__(self):
            self.upbit = _FakeOrderApi({"uuid-old": {"state": "wait"}})
            self.is_connected = True
            self.input_coins = _Text("KRW-BTC")
            self.combo_candle = _Combo(Config.DEFAULT_CANDLE)
            self.table = _DummyTable()
            self.btn_start = _Button()
            self.btn_stop = _Button()
            self.status_trading = _Label()
            self.status_realtime = _Label()
            self.strategy = None
            self.logger = _DummyLogger()
            self.price_thread = _DummyThread()
            self.order_service = UpbitOrderService()
            self.pending_orders = self.order_service.pending_orders
            self.universe = {}
            self.is_running = False
            self.daily_loss_triggered = False
            self.log_messages = []

        def calculate_target_price(self, *_):
            return 1000.0

        def calculate_ma(self, *_):
            return 900.0

        def set_table_item(self, *_):
            return None

        def stop_trading(self):
            self.is_running = False

        def log(self, msg):
            self.log_messages.append(msg)

    trader = _StartTrader()
    trader.order_service.mark_pending("KRW-OLD", "BUY", "uuid-old")

    with patch("upbit_trader_trading_controller.pyupbit.get_current_price", return_value=1100):
        trader.start_trading()

    assert trader.order_service.has_pending("KRW-OLD")


def test_execute_buy_uses_available_krw_after_reservation():
    class _BuyTrader(TraderTradingController):
        def __init__(self):
            self.upbit = _FakeOrderApi()
            self.order_service = UpbitOrderService()
            self.pending_orders = self.order_service.pending_orders
            self.universe = {"KRW-BTC": {"row": 0, "state": "감시중", "qty": 0}}
            self.strategy = None
            self.spin_betting = _Spin(50)
            self.logger = _DummyLogger()
            self.balance = 20000.0
            self._reserved_krw_by_ticker = {"KRW-ETH": 7000.0}
            self._active_session_id = 1

        def set_table_item(self, *_):
            return None

        def log(self, *_):
            return None

    trader = _BuyTrader()
    with patch("upbit_trader_trading_controller.QTimer.singleShot", side_effect=lambda *_: None):
        trader.execute_buy("KRW-BTC", 1000)

    assert trader.upbit.buy_calls
    _, buy_amount = trader.upbit.buy_calls[0]
    assert abs(buy_amount - 6500.0) < 1e-6
    pending = trader.order_service.get_pending("KRW-BTC")
    assert pending is not None
    assert abs(float(pending.get("reserved_krw", 0.0)) - 6500.0) < 1e-6


def test_batch_buy_respects_reserved_krw_and_skips_overbudget_orders():
    class _BatchTrader(TraderBatchController):
        def __init__(self):
            self.upbit = _FakeOrderApi()
            self.order_service = UpbitOrderService()
            self.input_coins = _Text("KRW-BTC,KRW-ETH")
            self.balance = 20000.0
            self._reserved_krw_by_ticker = {"KRW-OLD": 5000.0}
            self._active_session_id = 1
            self.universe = {}
            self.table = _DummyTable()
            self.chk_auto_start_after_batch = _Check(False)
            self.logs = []

        def _ensure_order_stability_state(self):
            return None

        def _get_available_krw(self):
            return max(0.0, self.balance - sum(self._reserved_krw_by_ticker.values()))

        def _reserve_krw_for_buy(self, ticker, amount, session_id=0):
            existing = self._reserved_krw_by_ticker.get(ticker, 0.0)
            available = self._get_available_krw() + existing
            if amount > available + 1e-8:
                return False
            self._reserved_krw_by_ticker[ticker] = amount
            return True

        def _release_reserved_krw(self, ticker):
            self._reserved_krw_by_ticker.pop(ticker, None)

        def _check_external_buy_execution(self, *args, **kwargs):
            return None

        def get_balance(self):
            return None

        def start_trading(self):
            return None

        def set_table_item(self, *_):
            return None

        def log(self, msg):
            self.logs.append(msg)

    trader = _BatchTrader()
    with patch(
        "upbit_trader_batch_controller.QMessageBox.warning",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch(
        "upbit_trader_batch_controller.QInputDialog.getText",
        return_value=("2", True),
    ), patch(
        "upbit_trader_batch_controller.QTimer.singleShot",
        side_effect=lambda *_: None,
    ):
        trader.execute_batch_buy()

    amounts = [amount for _, amount in trader.upbit.buy_calls]
    assert len(amounts) == 2
    assert sum(amounts) <= 15000.0 + 1e-6


def test_check_buy_execution_ignores_stale_session_callback():
    class _Trader(TraderTradingController):
        def __init__(self):
            self.upbit = _FakeOrderApi(
                {
                    "buy-1": {
                        "state": "done",
                        "executed_volume": "0.01",
                        "paid_fee": "100",
                        "trades": [{"price": "50000000", "volume": "0.01"}],
                    }
                }
            )
            self.order_service = UpbitOrderService()
            self.pending_orders = self.order_service.pending_orders
            self.universe = {"KRW-BTC": {"row": 0, "state": "주문중", "qty": 0, "invest_amt": 0}}
            self._reserved_krw_by_ticker = {"KRW-BTC": 6000.0}
            self._active_session_id = 2
            self.logger = _DummyLogger()

        def log(self, *_):
            return None

    trader = _Trader()
    trader.order_service.mark_pending("KRW-BTC", "BUY", "buy-1", session_id=1, reserved_krw=6000.0)
    trader.check_buy_execution("KRW-BTC", "buy-1", session_id=1)

    assert not trader.order_service.has_pending("KRW-BTC")
    assert trader.universe["KRW-BTC"]["state"] == "주문중"
    assert trader.universe["KRW-BTC"]["qty"] == 0


def test_check_sell_execution_handles_missing_universe_ticker_gracefully():
    class _Trader(TraderTradingController):
        def __init__(self):
            self.upbit = _FakeOrderApi(
                {
                    "sell-1": {
                        "state": "done",
                        "executed_volume": "1",
                        "executed_funds": "20000",
                        "paid_fee": "10",
                        "trades": [],
                    }
                }
            )
            self.order_service = UpbitOrderService()
            self.pending_orders = self.order_service.pending_orders
            self.universe = {}
            self.logger = _DummyLogger()

        def log(self, *_):
            return None

    trader = _Trader()
    trader.order_service.mark_pending("KRW-XRP", "SELL", "sell-1")
    trader.check_sell_execution("KRW-XRP", "sell-1", "테스트")
    assert not trader.order_service.has_pending("KRW-XRP")


def test_pending_reconcile_keeps_wait_clears_done_and_cancel():
    class _Trader(TraderTradingController):
        def __init__(self):
            self.upbit = _FakeOrderApi(
                {
                    "u-wait": {"state": "wait"},
                    "u-done": {"state": "done"},
                    "u-cancel": {"state": "cancel"},
                }
            )
            self.order_service = UpbitOrderService()
            self.pending_orders = self.order_service.pending_orders
            self._reserved_krw_by_ticker = {
                "KRW-A": 1000.0,
                "KRW-B": 2000.0,
                "KRW-C": 3000.0,
            }
            self.logger = _DummyLogger()

        def log(self, *_):
            return None

    trader = _Trader()
    trader.order_service.mark_pending("KRW-A", "BUY", "u-wait", reserved_krw=1000.0)
    trader.order_service.mark_pending("KRW-B", "BUY", "u-done", reserved_krw=2000.0)
    trader.order_service.mark_pending("KRW-C", "SELL", "u-cancel", reserved_krw=3000.0)

    trader._reconcile_pending_orders(force=False)

    assert trader.order_service.has_pending("KRW-A")
    assert not trader.order_service.has_pending("KRW-B")
    assert not trader.order_service.has_pending("KRW-C")
    assert "KRW-A" in trader._reserved_krw_by_ticker
    assert "KRW-B" not in trader._reserved_krw_by_ticker
    assert "KRW-C" not in trader._reserved_krw_by_ticker


def test_clear_pending_if_uuid_prevents_wrong_pending_cleanup():
    service = UpbitOrderService()
    service.mark_pending("KRW-BTC", "BUY", "uuid-1")

    assert not service.clear_pending_if_uuid("KRW-BTC", "uuid-2")
    assert service.has_pending("KRW-BTC")
    assert service.clear_pending_if_uuid("KRW-BTC", "uuid-1")
    assert not service.has_pending("KRW-BTC")
