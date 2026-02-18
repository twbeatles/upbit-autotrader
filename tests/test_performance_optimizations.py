import time
from unittest.mock import MagicMock, mock_open, patch

import pandas as pd

from upbit_config import Config
from upbit_price_thread import PriceUpdateThread
from upbit_strategy import UpbitStrategyManager
from upbit_trader_history_controller import TraderHistoryController
from upbit_trader_trading_controller import TraderTradingController


class _DummyLogger:
    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
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


class _Combo:
    def __init__(self, text):
        self._text = text

    def currentText(self):
        return self._text


class _Cell:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text

    def setForeground(self, *args, **kwargs):
        return None


class _Table:
    def __init__(self):
        self.set_item_calls = 0

    def setItem(self, *args, **kwargs):
        self.set_item_calls += 1

    def setUpdatesEnabled(self, *_):
        return None

    def item(self, *_):
        return None


class _IndicatorTrader(TraderTradingController):
    def __init__(self):
        self.combo_candle = _Combo(Config.DEFAULT_CANDLE)
        self.spin_rsi_period = _Spin(Config.DEFAULT_RSI_PERIOD)
        self.logger = _DummyLogger()


def _build_ohlcv(rows=60):
    idx = pd.date_range("2025-01-01", periods=rows, freq="h")
    base = pd.Series(range(rows), index=idx, dtype=float)
    close = 1000.0 + base
    return pd.DataFrame(
        {
            "open": close - 1,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": 10000 + (base * 10),
        },
        index=idx,
    )


def test_indicator_cache_deduplicates_ohlcv_calls():
    trader = _IndicatorTrader()
    df = _build_ohlcv()

    with patch("upbit_trader_trading_controller.pyupbit.get_ohlcv", return_value=df) as mock_ohlcv:
        ticker = "KRW-BTC"
        trader.calculate_rsi(ticker, 14)
        trader.calculate_macd(ticker)
        trader.calculate_bollinger_bands(ticker)
        trader.calculate_volume_avg(ticker, Config.DEFAULT_VOLUME_PERIOD)

    assert mock_ohlcv.call_count == 1


def test_check_buy_condition_reuses_snapshot_with_entry_scoring():
    class _BuyTrader(TraderTradingController):
        def __init__(self):
            self.strategy = None
            self.logger = _DummyLogger()
            self.combo_candle = _Combo(Config.DEFAULT_CANDLE)
            self.spin_rsi_period = _Spin(Config.DEFAULT_RSI_PERIOD)
            self.spin_rsi_upper = _Spin(80)
            self.spin_volume_mult = _Spin(1.0)
            self.spin_entry_score_threshold = _Spin(0)
            self.chk_use_rsi = _Check(False)
            self.chk_use_macd = _Check(False)
            self.chk_use_volume = _Check(False)
            self.chk_use_entry_scoring = _Check(True)
            self.chk_use_risk = _Check(False)
            self.buy_calls = 0

        def log(self, *_):
            return None

        def execute_buy(self, *_):
            self.buy_calls += 1

    trader = _BuyTrader()
    df = _build_ohlcv()
    info = {"target": 1000, "ma5": 995, "qty": 0, "state": "감시중"}

    with patch("upbit_trader_trading_controller.pyupbit.get_ohlcv", return_value=df) as mock_ohlcv:
        trader._check_buy_condition("KRW-BTC", 1100, info)

    assert trader.buy_calls == 1
    assert mock_ohlcv.call_count == 1


def test_mtf_trend_cache_reduces_repeated_ohlcv():
    class _Trader:
        chk_use_mtf = _Check(True)

        def log(self, *_):
            return None

    strategy = UpbitStrategyManager(_Trader())
    df = _build_ohlcv(20)

    with patch("upbit_strategy.pyupbit.get_ohlcv", return_value=df) as mock_ohlcv:
        strategy.check_mtf_condition("KRW-BTC")
        strategy.check_mtf_condition("KRW-BTC")

    assert mock_ohlcv.call_count == 2


def test_history_save_is_debounced():
    class _FakeSignal:
        def __init__(self):
            self.callback = None

        def connect(self, callback):
            self.callback = callback

    class _FakeTimer:
        def __init__(self, *_):
            self.timeout = _FakeSignal()
            self._active = False

        def setSingleShot(self, *_):
            return None

        def start(self, *_):
            self._active = True

        def isActive(self):
            return self._active

        def stop(self):
            self._active = False

    class _HistoryTrader(TraderHistoryController):
        def __init__(self):
            self.trade_history = []
            self.logger = _DummyLogger()

    trader = _HistoryTrader()

    with patch("upbit_trader_history_controller.QTimer", _FakeTimer), patch(
        "builtins.open", mock_open()
    ), patch("upbit_trader_history_controller.json.dump") as mock_dump:
        trader.add_trade_record("KRW-BTC", "BUY", 1000, 1)
        trader.add_trade_record("KRW-ETH", "BUY", 2000, 1)
        trader.add_trade_record("KRW-XRP", "SELL", 3000, 1)

        assert mock_dump.call_count == 0
        trader._flush_trade_history()
        assert mock_dump.call_count == 1


def test_price_thread_stop_returns_quickly():
    thread = PriceUpdateThread()
    thread.set_coins(["KRW-BTC"])

    with patch("upbit_price_thread.pyupbit.get_current_price", return_value={"KRW-BTC": 1000}):
        thread.start()
        time.sleep(0.05)
        start = time.perf_counter()
        thread.stop()
        assert thread.wait(1000)
        elapsed = time.perf_counter() - start

    assert elapsed < 0.5


def test_call_reduction_for_multi_ticker_multi_tick():
    trader = _IndicatorTrader()
    df = _build_ohlcv()

    with patch("upbit_trader_trading_controller.pyupbit.get_ohlcv", return_value=df) as mock_ohlcv:
        for _ in range(30):
            for i in range(10):
                ticker = f"KRW-T{i}"
                trader.calculate_rsi(ticker, 14)
                trader.calculate_macd(ticker)
                trader.calculate_bollinger_bands(ticker)
                trader.calculate_volume_avg(ticker, Config.DEFAULT_VOLUME_PERIOD)

    baseline = 10 * 30 * 4
    assert mock_ohlcv.call_count <= int(baseline * 0.3)


def test_on_price_update_avoids_setitem_when_ui_items_present():
    class _UiTrader(TraderTradingController):
        def __init__(self):
            self.is_running = True
            self.strategy = None
            self.table = _Table()
            self.universe = {
                "KRW-BTC": {
                    "row": 0,
                    "state": "대기",
                    "qty": 0,
                    "ui_items": {"price": _Cell()},
                }
            }

    trader = _UiTrader()
    trader.on_price_update({"KRW-BTC": 12345})

    assert trader.table.set_item_calls == 0
    assert trader.universe["KRW-BTC"]["ui_items"]["price"].text == "12,345"


def test_snapshot_expanded_indicators_still_single_api_call():
    trader = _IndicatorTrader()
    df = _build_ohlcv()
    interval = Config.CANDLE_INTERVALS[Config.DEFAULT_CANDLE]

    with patch("upbit_trader_trading_controller.pyupbit.get_ohlcv", return_value=df) as mock_ohlcv:
        snap = trader._get_indicator_snapshot("KRW-BTC", interval)
        assert snap is not None
        assert "ema_fast" in snap
        assert "donchian_upper" in snap
        assert "zscore" in snap
        assert "adx" in snap
        assert "realized_vol_pct" in snap

    assert mock_ohlcv.call_count == 1
