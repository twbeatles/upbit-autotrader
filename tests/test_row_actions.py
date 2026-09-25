"""Tests for holdings-table per-row quick trade buttons."""
import os
from typing import Any

from PyQt6.QtWidgets import QApplication, QTableWidget

from upbit_autotrader.controllers.ui_parts import order_ticket_ops, row_action_ops

_APP = None


def _app():
    global _APP
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication(["pytest-row-actions"])
    _APP = app
    return app


class _RowHolder:
    widget: Any
    table: Any
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

    def __init__(self):
        self.balance = 100000.0
        self.universe = {"KRW-BTC": {"qty": 0.5}}
        self.calls = []
        self.logs = []

    def _is_paper_mode(self):
        return True

    def _place_buy_order(self, ticker, amount, source="row", **kwargs):
        self.calls.append(("BUY", ticker, amount, source))
        return True, {"uuid": "row-buy-1"}, ""

    def _place_sell_order(self, ticker, qty, source="row", **kwargs):
        self.calls.append(("SELL", ticker, qty, source))
        return True, {"uuid": "row-sell-1"}, ""

    def log(self, msg):
        self.logs.append(msg)


def _holder_with_ticket():
    holder = _RowHolder()
    holder.table = QTableWidget()
    holder.table.setColumnCount(12)
    holder.table.insertRow(0)
    holder.widget = order_ticket_ops.build_order_ticket(holder)
    holder.chk_ticket_require_confirm.setChecked(False)
    return holder


def test_attach_row_buttons_creates_widgets():
    _app()
    holder = _holder_with_ticket()
    assert row_action_ops.attach_row_trade_buttons(holder, 0, "KRW-BTC") is True
    buy_btn = holder.table.cellWidget(0, row_action_ops.BUY_COL)
    sell_btn = holder.table.cellWidget(0, row_action_ops.SELL_COL)
    assert buy_btn is not None and buy_btn.text() == "매수"
    assert sell_btn is not None and sell_btn.text() == "매도"


def test_attach_row_buttons_rejects_bad_input():
    _app()
    holder = _holder_with_ticket()
    assert row_action_ops.attach_row_trade_buttons(holder, 0, "") is False
    holder.table = None
    assert row_action_ops.attach_row_trade_buttons(holder, 0, "KRW-BTC") is False


def test_row_quick_buy_uses_betting_ratio():
    _app()
    holder = _holder_with_ticket()
    assert row_action_ops.row_quick_buy(holder, "KRW-BTC") is True
    assert holder.calls[0][0] == "BUY"
    assert holder.calls[0][1] == "KRW-BTC"
    assert holder.calls[0][2] == 10000.0  # 10% default of 100k
    assert holder.combo_ticket_symbol.currentText() == "KRW-BTC"


def test_row_quick_sell_uses_holding_qty():
    _app()
    holder = _holder_with_ticket()
    assert row_action_ops.row_quick_sell(holder, "KRW-BTC") is True
    assert holder.calls[0][0] == "SELL"
    assert holder.calls[0][2] == 0.5


def test_row_quick_sell_without_holding_fails_safe():
    _app()
    holder = _holder_with_ticket()
    assert row_action_ops.row_quick_sell(holder, "KRW-ETH") is False
    assert holder.calls == []
    assert any("KRW-ETH" in msg for msg in holder.logs)
