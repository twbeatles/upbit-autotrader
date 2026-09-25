"""Tests for the read-only transfer (deposit/withdraw) history tab."""
import os
from typing import Any

from PyQt6.QtWidgets import QApplication

from upbit_autotrader.controllers.history_controller import (
    TraderHistoryController,
    _merge_transfers,
)

_APP = None


def _app():
    global _APP
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication(["pytest-transfer"])
    _APP = app
    return app


class _FakeUpbit:
    def __init__(self):
        self.deposit_calls = []
        self.withdraw_calls = []

    def get_deposits(self, currency=None, limit=100, page=1, order_by="desc"):
        self.deposit_calls.append((currency, limit))
        return [
            {"currency": "BTC", "amount": "0.01000000", "status": "ACCEPTED",
             "created_at": "2026-01-02T10:00:00", "txid": "dep-tx-1"},
        ]

    def get_withdraws(self, currency=None, limit=100, page=1, order_by="desc"):
        self.withdraw_calls.append((currency, limit))
        return [
            {"currency": "BTC", "amount": "0.00500000", "status": "DONE",
             "created_at": "2026-01-03T10:00:00", "txid": "wd-tx-1"},
        ]


class _TransferHolder(TraderHistoryController):
    widget: Any
    input_transfer_currency: Any
    spin_transfer_limit: Any
    lbl_transfer_status: Any
    transfer_table: Any

    upbit: Any

    def __init__(self, upbit=None):
        self.upbit = upbit


def test_merge_transfers_sorts_by_time_desc():
    deposits = [{"created_at": "2026-01-02T10:00:00"}]
    withdraws = [{"created_at": "2026-01-03T10:00:00"}]
    merged = _merge_transfers(deposits, withdraws)
    assert [e["side"] for e in merged] == ["withdraw", "deposit"]
    assert _merge_transfers(None, "bad") == []


def test_transfer_tab_refresh_populates_table():
    _app()
    holder = _TransferHolder(upbit=_FakeUpbit())
    holder.widget = TraderHistoryController.create_transfer_tab(holder)
    holder.refresh_transfer_history()
    assert holder.transfer_table.rowCount() == 2
    # Newest first: withdrawal row on top.
    assert holder.transfer_table.item(0, 1).text() == "📤 출금"
    assert holder.transfer_table.item(1, 1).text() == "📥 입금"
    assert holder.transfer_table.item(0, 5).text() == "wd-tx-1"
    assert "입금 1건" in holder.lbl_transfer_status.text()


def test_transfer_tab_currency_filter_forwarded():
    _app()
    holder = _TransferHolder(upbit=_FakeUpbit())
    holder.widget = TraderHistoryController.create_transfer_tab(holder)
    holder.input_transfer_currency.setText("btc")
    holder.spin_transfer_limit.setValue(5)
    holder.refresh_transfer_history()
    assert holder.upbit.deposit_calls[0] == ("BTC", 5)
    assert holder.upbit.withdraw_calls[0] == ("BTC", 5)


def test_transfer_tab_without_api_shows_hint():
    _app()
    holder = _TransferHolder(upbit=None)
    holder.widget = TraderHistoryController.create_transfer_tab(holder)
    holder.refresh_transfer_history()
    assert holder.transfer_table.rowCount() == 0
    assert "API 연결" in holder.lbl_transfer_status.text()
