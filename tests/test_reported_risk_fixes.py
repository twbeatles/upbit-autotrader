import datetime
import json
import tempfile
from unittest.mock import patch

import pandas as pd
from PyQt6.QtWidgets import QMessageBox

from upbit_analytics import UpbitTradingAnalytics
from upbit_config import Config
from upbit_order_service import UpbitOrderService
from upbit_paper_order_service import UpbitPaperOrderService
from upbit_trader_history_controller import TraderHistoryController
from upbit_trader_trading_controller import TraderTradingController


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

    def setRowCount(self, count):
        self._rows = count

    def insertRow(self, row):
        self._rows = max(self._rows, row + 1)

    def setItem(self, *_):
        return None

    def item(self, *_):
        return None

    def setUpdatesEnabled(self, *_):
        return None

    def rowCount(self):
        return self._rows


class _Thread:
    def __init__(self):
        self.coins = []

    def set_coins(self, coins):
        self.coins = list(coins)

    def start(self):
        return None

    def isRunning(self):
        return False

    def stop(self):
        return None

    def wait(self, *_):
        return True


class _Logger:
    def info(self, *_):
        return None

    def warning(self, *_):
        return None

    def error(self, *_):
        return None


def test_analytics_uses_timestamp_key_for_daily_and_monthly():
    now = datetime.datetime.now().replace(microsecond=0)
    rows = [
        {"timestamp": now.isoformat(), "ticker": "KRW-BTC", "profit": 1200},
        {"timestamp": (now - datetime.timedelta(days=1)).isoformat(), "ticker": "KRW-ETH", "profit": -300},
    ]
    with tempfile.TemporaryDirectory() as td:
        path = f"{td}/history.json"
        with open(path, "w", encoding="utf-8") as fp:
            json.dump(rows, fp, ensure_ascii=False)
        analytics = UpbitTradingAnalytics(path)
        daily = analytics.get_daily_performance(days=30)
        monthly = analytics.get_monthly_summary()

    assert daily
    assert now.strftime("%Y-%m") in monthly


def test_clear_today_history_handles_legacy_and_malformed_records():
    today = datetime.datetime.now().date().isoformat()

    class _History(TraderHistoryController):
        def __init__(self):
            self.trade_history = [
                {"timestamp": f"{today}T01:23:45", "ticker": "KRW-BTC"},
                {"datetime": f"{today}T05:00:00", "ticker": "KRW-ETH"},
                {"timestamp": "not-a-timestamp", "ticker": "KRW-XRP"},
                {"ticker": "KRW-ADA"},
            ]
            self.history_table = _Table()

        def save_trade_history(self):
            return None

        def _load_history_to_table(self):
            return None

        def log(self, *_):
            return None

    trader = _History()
    with patch(
        "upbit_trader_history_controller.QMessageBox.question",
        return_value=QMessageBox.StandardButton.Yes,
    ):
        trader.clear_today_history()

    remaining = [r.get("ticker") for r in trader.trade_history if isinstance(r, dict)]
    assert "KRW-BTC" not in remaining
    assert "KRW-ETH" not in remaining
    assert "KRW-XRP" in remaining
    assert "KRW-ADA" in remaining


def test_indicator_snapshot_volume_avg_uses_volume_period_window():
    class _Trader(TraderTradingController):
        def __init__(self):
            self.spin_rsi_period = _Spin(Config.DEFAULT_RSI_PERIOD)

    idx = pd.date_range("2026-01-01", periods=40, freq="h")
    base = pd.Series(range(40), index=idx, dtype=float)
    df = pd.DataFrame(
        {
            "open": 1000 + base,
            "high": 1005 + base,
            "low": 995 + base,
            "close": 1000 + base,
            "volume": 1 + base,
        },
        index=idx,
    )

    trader = _Trader()
    with patch("upbit_trader_trading_controller.pyupbit.get_ohlcv", return_value=df):
        snap = trader._get_indicator_snapshot("KRW-BTC", "minute240", volume_period=3)

    assert snap is not None
    assert abs(float(snap["avg_volume"]) - 38.0) < 1e-9


def test_start_trading_allows_paper_mode_without_login_and_seeds_balance():
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
            self.lbl_balance = _Label()
            self.strategy = None
            self.logger = _Logger()
            self.price_thread = _Thread()
            self.order_service = UpbitOrderService()
            self.pending_orders = self.order_service.pending_orders
            self.paper_order_service = UpbitPaperOrderService(fee_rate=0.0005, slippage_bps=0)
            self.chk_paper_trading = _Check(True)
            self.chk_paper_allow_without_login = _Check(True)
            self.spin_paper_fee_bps = _Spin(5.0)
            self.spin_paper_slippage_bps = _Spin(0.0)
            self.spin_paper_seed_krw = _Spin(10_000_000.0)
            self.universe = {}
            self.is_running = False
            self.daily_loss_triggered = False
            self.balance = 0.0
            self.initial_balance = 0.0
            self._paper_seeded = False

        def calculate_target_price(self, *_):
            return 1000.0

        def calculate_ma(self, *_):
            return 900.0

        def set_table_item(self, *_):
            return None

        def log(self, *_):
            return None

    trader = _Trader()
    with patch("upbit_trader_trading_controller.pyupbit.get_current_price", return_value=1100):
        trader.start_trading()

    assert trader.is_running
    assert trader.universe
    assert trader.paper_order_service.get_krw_balance() >= 10_000_000.0
