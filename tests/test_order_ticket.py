"""Tests for the securities-app style order ticket widget."""
import os
from typing import Any

from PyQt6.QtWidgets import QApplication

from upbit_autotrader.controllers.ui_parts import order_ticket_ops

_APP = None


def _app():
    global _APP
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication(["pytest-ticket"])
    _APP = app
    return app


class _TicketHolder:
    widget: Any
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
        self.calls = []
        self.chk_paper_trading = None

    def _is_paper_mode(self):
        return True

    def _place_buy_order(self, ticker, amount, source="order_ticket", **kwargs):
        self.calls.append(("BUY", ticker, amount, source))
        return True, {"uuid": "ticket-buy-1"}, ""

    def _place_sell_order(self, ticker, qty, source="order_ticket", **kwargs):
        self.calls.append(("SELL", ticker, qty, source))
        return True, {"uuid": "ticket-sell-1"}, ""


def test_build_order_ticket_exposes_expected_surface():
    _app()
    holder = _TicketHolder()
    widget = order_ticket_ops.build_order_ticket(holder)
    holder.widget = widget
    assert holder.combo_ticket_symbol is not None
    assert holder.combo_ticket_type is not None
    assert holder.spin_ticket_price is not None
    assert holder.spin_ticket_amount is not None
    assert holder.chk_ticket_require_confirm is not None
    assert holder.btn_ticket_buy is not None
    assert holder.btn_ticket_sell is not None
    assert holder.lbl_ticket_mode.text() == "PAPER"
    assert widget is not None


def test_ticket_preset_sets_amount_from_balance():
    _app()
    holder = _TicketHolder()
    holder.widget = order_ticket_ops.build_order_ticket(holder)
    holder.combo_ticket_type.setCurrentText("시장가")
    order_ticket_ops._apply_ticket_preset(holder, 50)
    assert holder.spin_ticket_amount.value() == 50000.0


def test_submit_ticket_order_paper_no_confirm():
    _app()
    holder = _TicketHolder()
    holder.widget = order_ticket_ops.build_order_ticket(holder)
    holder.chk_ticket_require_confirm.setChecked(False)
    holder.combo_ticket_symbol.setCurrentText("KRW-BTC")
    holder.spin_ticket_amount.setValue(10000)
    ok = order_ticket_ops.submit_ticket_order(holder, "BUY")
    assert ok is True
    assert holder.calls[0][0] == "BUY"
    assert holder.calls[0][1] == "KRW-BTC"


def test_ticket_dry_run_without_client_fails_safe():
    _app()
    holder = _TicketHolder()
    holder.widget = order_ticket_ops.build_order_ticket(holder)
    holder.combo_ticket_symbol.setCurrentText("KRW-BTC")
    holder.spin_ticket_amount.setValue(5000)
    assert order_ticket_ops.ticket_dry_run(holder) is False
