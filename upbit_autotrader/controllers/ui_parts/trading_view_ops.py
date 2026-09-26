"""Spot trading view: securities-app style 4-pane (watchlist/chart/orderbook/ticket).

Left = watchlist, center = price chart, right = orderbook + recent trades,
bottom = order ticket (reuses order_ticket_ops). Selecting a watchlist row
drives chart + orderbook + trades + ticket symbol.
"""
from typing import Any

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from upbit_autotrader.core.config import Config
from upbit_autotrader.ui import design_tokens as tokens

CHART_TIMEFRAMES = (
    ("5분", "minutes", 5),
    ("15분", "minutes", 15),
    ("1시간", "minutes", 60),
    ("4시간", "minutes", 240),
    ("일봉", "days", 0),
    ("주봉", "weeks", 0),
)

UP_COLOR = "#e63946"
DOWN_COLOR = "#4361ee"


def _chart_palette(widget) -> dict:
    try:
        from upbit_autotrader.ui.theme import is_dark_mode
        dark = bool(is_dark_mode())
    except Exception:
        dark = True
    try:
        widget._chart_dark = dark
    except Exception:
        pass
    return tokens.chart_colors(dark)


class PriceChartWidget(QWidget):
    """Dependency-free close-price line chart (QPainter, dark-mode aware)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._series: list = []
        self.setMinimumSize(200, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_series(self, prices) -> int:
        clean = []
        for value in prices or []:
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if number > 0:
                clean.append(number)
        self._series = clean
        self.update()
        return len(self._series)

    def series(self) -> list:
        return list(self._series)

    def paintEvent(self, a0) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        chart_pal = _chart_palette(self)
        painter.fillRect(self.rect(), QColor(chart_pal["background"]))
        if len(self._series) < 2:
            painter.setPen(QPen(QColor(chart_pal["grid"])))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "차트 데이터 없음")
            return
        low = min(self._series)
        high = max(self._series)
        span = (high - low) or 1.0
        metrics = painter.fontMetrics()
        high_text = f"{high:,.0f}"
        low_text = f"{low:,.0f}"
        gutter = (
            max(10, metrics.horizontalAdvance(high_text), metrics.horizontalAdvance(low_text)) + 16
        )
        top_pad = metrics.ascent() + 10
        bottom_pad = metrics.descent() + 10
        plot_w = max(1.0, float(self.width() - gutter - 8))
        plot_h = max(1.0, float(self.height() - top_pad - bottom_pad))
        count = len(self._series)
        path = QPainterPath()
        for idx, value in enumerate(self._series):
            x = gutter + plot_w * idx / (count - 1)
            y = top_pad + plot_h * (1.0 - (value - low) / span)
            point = QPointF(x, y)
            if idx == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        rising = self._series[-1] >= self._series[0]
        pen = QPen(QColor(UP_COLOR if rising else DOWN_COLOR))
        pen.setWidthF(2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)
        painter.setPen(QPen(QColor(chart_pal["text"])))
        painter.drawText(8, top_pad - 4, high_text)
        painter.drawText(8, self.height() - 4, low_text)


def _trading_markets(self) -> list:
    coins_widget = getattr(self, "input_coins", None)
    text = ""
    if coins_widget is not None and hasattr(coins_widget, "text"):
        text = str(coins_widget.text())
    if not text.strip():
        text = str(Config.DEFAULT_COINS)
    return [c.strip() for c in text.split(",") if c.strip()]


def build_trading_view(self) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(tokens.SPACE_XS)
    layout.setContentsMargins(tokens.SPACE_SM, tokens.SPACE_SM, tokens.SPACE_SM, tokens.SPACE_SM)

    header = QHBoxLayout()
    self.lbl_trading_symbol = QLabel("관심종목을 선택하세요")
    symbol_font = self.lbl_trading_symbol.font(); symbol_font.setPointSize(tokens.FONT_SECTION_TITLE); symbol_font.setBold(True); self.lbl_trading_symbol.setFont(symbol_font)
    header.addWidget(self.lbl_trading_symbol)
    header.addStretch(1)
    btn_refresh = QPushButton("새로고침")
    btn_refresh.setToolTip("관심종목·차트·호가·체결을 모두 갱신합니다.")
    btn_refresh.clicked.connect(lambda: refresh_trading_all(self))
    header.addWidget(btn_refresh)
    layout.addLayout(header)

    panes = QSplitter(Qt.Orientation.Horizontal)
    panes.setChildrenCollapsible(False)
    panes.setHandleWidth(6)

    watch_group = QGroupBox("관심종목")
    watch_layout = QVBoxLayout(watch_group)
    self.list_trading_watchlist = QListWidget()
    self.list_trading_watchlist.itemClicked.connect(
        lambda item: select_trading_symbol(self, str(item.data(Qt.ItemDataRole.UserRole) or ""))
    )
    watch_layout.addWidget(self.list_trading_watchlist)
    watch_group.setMinimumWidth(150)
    panes.addWidget(watch_group)

    center = QWidget()
    center_layout = QVBoxLayout(center)
    center_layout.setContentsMargins(0, 0, 0, 0)
    chart_bar = QHBoxLayout()
    chart_bar.addWidget(QLabel("차트"))
    self.combo_trading_timeframe = QComboBox()
    for label, _kind, _unit in CHART_TIMEFRAMES:
        self.combo_trading_timeframe.addItem(label)
    self.combo_trading_timeframe.setCurrentText("일봉")
    self.combo_trading_timeframe.currentTextChanged.connect(lambda _t: refresh_trading_chart(self))
    chart_bar.addWidget(self.combo_trading_timeframe)
    chart_bar.addStretch(1)
    center_layout.addLayout(chart_bar)
    self.chart_trading = PriceChartWidget()
    center_layout.addWidget(self.chart_trading, 1)
    self.lbl_trading_status = QLabel("대기 중")
    center_layout.addWidget(self.lbl_trading_status)
    center.setMinimumWidth(260)
    panes.addWidget(center)

    right = QWidget()
    right_layout = QVBoxLayout(right)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.addWidget(QLabel("호가"))
    self.table_trading_orderbook = QTableWidget()
    self.table_trading_orderbook.setColumnCount(2)
    self.table_trading_orderbook.setHorizontalHeaderLabels(["가격", "잔량"])
    ob_header = self.table_trading_orderbook.horizontalHeader()
    if ob_header is not None:
        ob_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    self.table_trading_orderbook.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    self.table_trading_orderbook.setMinimumHeight(120)
    right_layout.addWidget(self.table_trading_orderbook, 3)
    right_layout.addWidget(QLabel("최근 체결"))
    self.list_trading_trades = QListWidget()
    self.list_trading_trades.setMinimumHeight(80)
    right_layout.addWidget(self.list_trading_trades, 2)
    right.setMinimumWidth(200)
    panes.addWidget(right)

    panes.setStretchFactor(0, 1)
    panes.setStretchFactor(1, 2)
    panes.setStretchFactor(2, 1)
    panes.setSizes([220, 560, 260])
    layout.addWidget(panes, 1)

    try:
        from upbit_autotrader.controllers.ui_parts import order_ticket_ops as _ticket_ops
        layout.addWidget(_ticket_ops.build_order_ticket(self))
    except Exception:
        pass
    refresh_trading_watchlist(self)
    return widget


def current_trading_symbol(self) -> str:
    return str(getattr(self, "_trading_symbol", "") or "")


def select_trading_symbol(self, market: str) -> str:
    market = str(market or "").strip()
    if not market:
        return ""
    self._trading_symbol = market
    header = getattr(self, "lbl_trading_symbol", None)
    if header is not None:
        header.setText(market)
    ticket_combo = getattr(self, "combo_ticket_symbol", None)
    if ticket_combo is not None and hasattr(ticket_combo, "setCurrentText"):
        try:
            ticket_combo.setCurrentText(market)
        except Exception:
            pass
    refresh_trading_chart(self)
    refresh_trading_orderbook(self)
    refresh_trading_trades(self)
    return market


def refresh_trading_all(self) -> None:
    refresh_trading_watchlist(self)
    refresh_trading_chart(self)
    refresh_trading_orderbook(self)
    refresh_trading_trades(self)


def refresh_trading_watchlist(self) -> int:
    watchlist = getattr(self, "list_trading_watchlist", None)
    if watchlist is None:
        return 0
    watchlist.clear()
    markets = _trading_markets(self)
    quotes = {}
    upbit = getattr(self, "upbit", None)
    get_tickers = getattr(upbit, "get_tickers", None)
    if callable(get_tickers):
        try:
            tick_rows: Any = get_tickers(markets) or []
            for row in tick_rows:
                if isinstance(row, dict) and row.get("market"):
                    quotes[str(row["market"])] = row
        except Exception:
            quotes = {}
    for market in markets:
        row = quotes.get(market, {})
        try:
            price = float(row.get("trade_price", 0.0) or 0.0)
        except (TypeError, ValueError):
            price = 0.0
        try:
            change = float(row.get("signed_change_rate", 0.0) or 0.0) * 100.0
        except (TypeError, ValueError):
            change = 0.0
        price_text = f"{price:,.0f}" if price > 0 else "-"
        item = QListWidgetItem(f"{market}\n{price_text} ({change:+.2f}%)")
        item.setData(Qt.ItemDataRole.UserRole, market)
        if change > 0:
            item.setForeground(QColor(UP_COLOR))
        elif change < 0:
            item.setForeground(QColor(DOWN_COLOR))
        watchlist.addItem(item)
    if markets and not current_trading_symbol(self):
        select_trading_symbol(self, markets[0])
    return len(markets)


def _fetch_chart_closes(self, market: str, timeframe_label: str, count: int = 120) -> list:
    upbit = getattr(self, "upbit", None)
    if upbit is None or not market:
        return []
    kind, unit = "days", 0
    for label, label_kind, label_unit in CHART_TIMEFRAMES:
        if label == timeframe_label:
            kind, unit = label_kind, label_unit
            break
    try:
        if kind == "minutes":
            candles = upbit.get_candles_minutes(market, unit=unit or 60, count=count)
        elif kind == "weeks":
            candles = upbit.get_candles_weeks(market, count=count)
        else:
            candles = upbit.get_candles_days(market, count=count)
    except Exception:
        return []
    closes = []
    for candle in reversed(candles or []):
        if not isinstance(candle, dict):
            continue
        try:
            closes.append(float(candle.get("trade_price", 0.0) or 0.0))
        except (TypeError, ValueError):
            continue
    return [c for c in closes if c > 0]


def refresh_trading_chart(self) -> int:
    chart = getattr(self, "chart_trading", None)
    if chart is None:
        return 0
    timeframe_combo = getattr(self, "combo_trading_timeframe", None)
    timeframe = "일봉"
    if timeframe_combo is not None and hasattr(timeframe_combo, "currentText"):
        timeframe = str(timeframe_combo.currentText())
    closes = _fetch_chart_closes(self, current_trading_symbol(self), timeframe)
    count = chart.set_series(closes)
    status = getattr(self, "lbl_trading_status", None)
    if status is not None:
        status.setText(f"{current_trading_symbol(self)} {timeframe} {count}개" if count else "차트 데이터 없음")
    return count


def refresh_trading_orderbook(self) -> int:
    table = getattr(self, "table_trading_orderbook", None)
    if table is None:
        return 0
    table.setRowCount(0)
    upbit = getattr(self, "upbit", None)
    get_orderbook = getattr(upbit, "get_orderbook", None)
    if not callable(get_orderbook):
        return 0
    try:
        books: Any = get_orderbook(current_trading_symbol(self)) or []
    except Exception:
        return 0
    if not books or not isinstance(books[0], dict):
        return 0
    units = books[0].get("orderbook_units") or []
    asks = [(u.get("ask_price"), u.get("ask_size")) for u in units if isinstance(u, dict)]
    bids = [(u.get("bid_price"), u.get("bid_size")) for u in units if isinstance(u, dict)]
    rows = list(reversed(asks[-5:])) + bids[:5]
    for price, size in rows:
        row = table.rowCount()
        table.insertRow(row)
        try:
            price_text = f"{float(price or 0):,.0f}"
        except (TypeError, ValueError):
            price_text = "-"
        try:
            size_text = f"{float(size or 0):.4f}"
        except (TypeError, ValueError):
            size_text = "-"
        price_item = QTableWidgetItem(price_text)
        is_ask = row < len(asks[-5:])
        price_item.setForeground(QColor(DOWN_COLOR if is_ask else UP_COLOR))
        table.setItem(row, 0, price_item)
        table.setItem(row, 1, QTableWidgetItem(size_text))
    return table.rowCount()


def refresh_trading_trades(self) -> int:
    trades_widget = getattr(self, "list_trading_trades", None)
    if trades_widget is None:
        return 0
    trades_widget.clear()
    upbit = getattr(self, "upbit", None)
    get_trades = getattr(upbit, "get_recent_trades", None)
    if not callable(get_trades):
        return 0
    try:
        trades: Any = get_trades(current_trading_symbol(self), count=20) or []
    except Exception:
        return 0
    for trade in trades:
        if not isinstance(trade, dict):
            continue
        try:
            price = float(trade.get("trade_price", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        try:
            volume = float(trade.get("trade_volume", 0.0) or 0.0)
        except (TypeError, ValueError):
            volume = 0.0
        side = str(trade.get("ask_bid", "")).upper()
        item = QListWidgetItem(f"{price:,.0f} ({volume:.4f})")
        if side == "BID":
            item.setForeground(QColor(UP_COLOR))
        elif side == "ASK":
            item.setForeground(QColor(DOWN_COLOR))
        trades_widget.addItem(item)
    return trades_widget.count()
