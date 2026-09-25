"""Tests for the 4-pane spot trading view (watchlist/chart/orderbook/ticket)."""
import os
from types import SimpleNamespace
from typing import Any

from PyQt6.QtWidgets import QApplication, QSplitter

from upbit_autotrader.controllers.ui_parts import trading_view_ops
from upbit_autotrader.controllers.ui_parts.trading_view_ops import PriceChartWidget

_APP = None


def _app():
    global _APP
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication(["pytest-trading-view"])
    _APP = app
    return app


class _FakeUpbit:
    def __init__(self, markets):
        self._markets = list(markets)

    def get_tickers(self, markets):
        if isinstance(markets, str):
            markets = [markets]
        return [
            {"market": m, "trade_price": 100000.0, "signed_change_rate": 0.023}
            for m in (markets or self._markets)
        ]

    def get_candles_days(self, market, count=120, to=None):
        return [{"trade_price": 100.0 + i} for i in range(count)]

    def get_candles_weeks(self, market, count=120, to=None):
        return [{"trade_price": 100.0 + i} for i in range(count)]

    def get_candles_minutes(self, market, unit=60, count=120, to=None):
        return [{"trade_price": 100.0 + i} for i in range(count)]

    def get_orderbook(self, markets, count=None):
        units = [
            {
                "ask_price": 101000.0 + i * 100,
                "ask_size": 0.1 + i * 0.01,
                "bid_price": 100000.0 - i * 100,
                "bid_size": 0.2 + i * 0.01,
            }
            for i in range(5)
        ]
        return [{"market": markets, "orderbook_units": units}]

    def get_recent_trades(self, market, count=20, **kwargs):
        return [
            {"trade_price": 100000.0, "trade_volume": 0.001, "ask_bid": "BID"}
            for _ in range(3)
        ]


class _ViewHolder:
    widget: Any
    list_trading_watchlist: Any
    lbl_trading_symbol: Any
    combo_trading_timeframe: Any
    chart_trading: Any
    lbl_trading_status: Any
    table_trading_orderbook: Any
    list_trading_trades: Any
    combo_ticket_symbol: Any
    combo_ticket_type: Any
    spin_ticket_price: Any
    spin_ticket_amount: Any
    chk_ticket_require_confirm: Any
    btn_ticket_dryrun: Any
    btn_ticket_buy: Any
    btn_ticket_sell: Any
    lbl_ticket_mode: Any
    lbl_ticket_status: Any

    def __init__(self, markets="KRW-BTC,KRW-ETH", upbit=None):
        self.input_coins = SimpleNamespace(text=lambda: markets)
        self.upbit = upbit
        self.balance = 100000.0
        self.calls = []

    def _is_paper_mode(self):
        return True

    def _place_buy_order(self, ticker, amount, source="order_ticket", **kwargs):
        self.calls.append(("BUY", ticker, amount))
        return True, {"uuid": "tv-buy-1"}, ""

    def _place_sell_order(self, ticker, qty, source="order_ticket", **kwargs):
        self.calls.append(("SELL", ticker, qty))
        return True, {"uuid": "tv-sell-1"}, ""


def _holder_with_upbit():
    markets = ["KRW-BTC", "KRW-ETH"]
    holder = _ViewHolder(upbit=_FakeUpbit(markets))
    holder.widget = trading_view_ops.build_trading_view(holder)
    return holder


def test_build_trading_view_populates_all_panes():
    _app()
    holder = _holder_with_upbit()
    assert holder.list_trading_watchlist.count() == 2
    # First market auto-selected on watchlist refresh.
    assert holder.lbl_trading_symbol.text() == "KRW-BTC"
    assert len(holder.chart_trading.series()) == 120
    assert holder.table_trading_orderbook.rowCount() == 10
    assert holder.list_trading_trades.count() == 3


def test_select_symbol_drives_ticket_and_panes():
    _app()
    holder = _holder_with_upbit()
    assert trading_view_ops.select_trading_symbol(holder, "KRW-ETH") == "KRW-ETH"
    assert holder.lbl_trading_symbol.text() == "KRW-ETH"
    assert holder.combo_ticket_symbol.currentText() == "KRW-ETH"
    assert len(holder.chart_trading.series()) == 120


def test_select_empty_symbol_is_noop():
    _app()
    holder = _holder_with_upbit()
    assert trading_view_ops.select_trading_symbol(holder, "") == ""
    assert holder.lbl_trading_symbol.text() == "KRW-BTC"


def test_trading_view_without_upbit_degrades_gracefully():
    _app()
    holder = _ViewHolder(upbit=None)
    holder.widget = trading_view_ops.build_trading_view(holder)
    assert holder.list_trading_watchlist.count() == 2
    assert holder.chart_trading.series() == []
    assert holder.table_trading_orderbook.rowCount() == 0
    assert holder.list_trading_trades.count() == 0


def test_price_chart_filters_and_paints():
    _app()
    chart = PriceChartWidget()
    assert chart.set_series([0, -1, None, "bad", 10.0, 20.0]) == 2
    assert chart.series() == [10.0, 20.0]
    pixmap = chart.grab()
    assert pixmap.width() > 0
    chart.set_series([])
    pixmap = chart.grab()
    assert pixmap.width() > 0


def test_price_chart_paints_at_multiple_window_sizes():
    """Chart must paint cleanly at 1080p and HiDPI window sizes."""
    _app()
    chart = PriceChartWidget()
    assert chart.set_series([100.0 + i * 0.5 for i in range(120)]) == 120
    for width, height in [(320, 220), (640, 400), (960, 540), (1280, 720)]:
        chart.resize(width, height)
        pixmap = chart.grab()
        assert not pixmap.isNull()
        assert pixmap.width() == width
        assert pixmap.height() == height


def test_price_chart_paints_degenerate_series_and_tiny_sizes():
    """Single-point/empty/huge series and tiny widgets must not break painting."""
    _app()
    chart = PriceChartWidget()
    chart.resize(10, 10)
    assert chart.set_series([42.0]) == 1
    assert not chart.grab().isNull()
    chart.set_series([])
    assert not chart.grab().isNull()
    assert chart.set_series([100.0] * 5000) == 5000
    chart.resize(800, 600)
    assert not chart.grab().isNull()


def test_trading_view_layout_has_dpi_safe_constraints():
    """Splitter panes keep minimum widths; chart stays expandable."""
    _app()
    holder = _holder_with_upbit()
    assert holder.chart_trading.minimumWidth() >= 200
    assert holder.chart_trading.minimumHeight() >= 200
    panes = holder.widget.findChild(QSplitter)
    assert panes is not None
    assert panes.handleWidth() >= 4
    assert panes.count() == 3
    for index in range(panes.count()):
        assert panes.widget(index).minimumWidth() > 0
