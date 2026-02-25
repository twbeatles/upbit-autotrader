from unittest.mock import patch

from upbit_config import Config
from upbit_order_service import UpbitOrderService
from upbit_paper_order_service import UpbitPaperOrderService
from upbit_trader_trading_controller import TraderTradingController


class _Text:
    def __init__(self, value):
        self._value = value

    def text(self):
        return self._value


class _Combo:
    def __init__(self, value):
        self._value = value

    def currentText(self):
        return self._value


class _Button:
    def __init__(self):
        self.enabled = None

    def setEnabled(self, enabled):
        self.enabled = bool(enabled)


class _Label:
    def __init__(self):
        self.value = ""

    def setText(self, value):
        self.value = value

    def setStyleSheet(self, *_):
        return None


class _Table:
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


class _Thread:
    def __init__(self):
        self.coins = []
        self.running = False

    def set_coins(self, coins):
        self.coins = list(coins)

    def start(self):
        self.running = True

    def isRunning(self):
        return self.running

    def stop(self):
        self.running = False

    def wait(self, *_):
        return True


class _Check:
    def __init__(self, checked):
        self._checked = checked

    def isChecked(self):
        return self._checked


class _Spin:
    def __init__(self, value):
        self._value = value

    def value(self):
        return self._value


class _DummyLogger:
    def info(self, *_):
        return None

    def warning(self, *_):
        return None

    def error(self, *_):
        return None


class _BaseTrader(TraderTradingController):
    def __init__(self):
        self.input_coins = _Text("KRW-BTC")
        self.combo_candle = _Combo(Config.DEFAULT_CANDLE)
        self.table = _Table()
        self.btn_start = _Button()
        self.btn_stop = _Button()
        self.status_trading = _Label()
        self.status_realtime = _Label()
        self.lbl_balance = _Label()
        self.price_thread = _Thread()
        self.order_service = UpbitOrderService()
        self.pending_orders = self.order_service.pending_orders
        self.paper_order_service = UpbitPaperOrderService(fee_rate=0.0005, slippage_bps=0.0)
        self.chk_enable_account_wide_sync = _Check(True)
        self.spin_paper_fee_bps = _Spin(5.0)
        self.spin_paper_slippage_bps = _Spin(0.0)
        self.spin_paper_seed_krw = _Spin(1_000_000.0)
        self.strategy = None
        self.logger = _DummyLogger()
        self.universe = {}
        self.is_running = False
        self.daily_loss_triggered = False
        self.balance = 0.0
        self.initial_balance = 1_000_000.0

    def calculate_target_price(self, *_):
        return 1000.0

    def calculate_ma(self, *_):
        return 900.0

    def set_table_item(self, *_):
        return None

    def log(self, *_):
        return None


class _LiveTrader(_BaseTrader):
    def __init__(self):
        super().__init__()
        self.upbit = object()
        self.is_connected = True
        self.chk_paper_trading = _Check(False)
        self.chk_paper_allow_without_login = _Check(False)
        self.balance = 1_000_000.0

    def get_account_holdings(self):
        return [
            {
                "ticker": "KRW-XRP",
                "qty": 10.0,
                "buy_price": 1000.0,
                "current_price": 1200.0,
                "value": 12000.0,
            }
        ]


class _PaperTrader(_BaseTrader):
    def __init__(self):
        super().__init__()
        self.upbit = None
        self.is_connected = False
        self.chk_paper_trading = _Check(True)
        self.chk_paper_allow_without_login = _Check(True)
        self.balance = 0.0

    def get_account_holdings(self):
        return [
            {
                "ticker": "KRW-ETH",
                "qty": 1.5,
                "buy_price": 2_000_000.0,
                "current_price": 2_100_000.0,
                "value": 3_150_000.0,
            }
        ]


def test_startup_sync_merges_watchlist_and_external_live_holdings():
    trader = _LiveTrader()

    with patch("upbit_trader_trading_controller.pyupbit.get_current_price", return_value=1100.0):
        trader.start_trading()

    assert trader.is_running is True
    assert "KRW-BTC" in trader.universe
    assert "KRW-XRP" in trader.universe
    assert trader.universe["KRW-XRP"]["state"] == "보유중"
    assert abs(float(trader.universe["KRW-XRP"]["qty"]) - 10.0) < 1e-9
    assert abs(float(trader.universe["KRW-XRP"]["buy_price"]) - 1000.0) < 1e-9


def test_startup_sync_works_in_paper_mode_without_login():
    trader = _PaperTrader()

    with patch("upbit_trader_trading_controller.pyupbit.get_current_price", return_value=1100.0):
        trader.start_trading()

    assert trader.is_running is True
    assert "KRW-BTC" in trader.universe
    assert "KRW-ETH" in trader.universe
    assert trader.universe["KRW-ETH"]["state"] == "보유중"
    assert abs(float(trader.universe["KRW-ETH"]["qty"]) - 1.5) < 1e-9
