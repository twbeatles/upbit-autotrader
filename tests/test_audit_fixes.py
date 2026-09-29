"""Regression tests for PROJECT_AUDIT.md Phase 1-3 fixes.

Each test encodes the corrected behavior; on the pre-fix code the
order-ticket, history-atomicity, settings-split and binding-guard tests fail.
"""
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from PyQt6.QtWidgets import QApplication

from upbit_autotrader.controllers.ui_parts import order_ticket_ops
from upbit_autotrader.core.config import Config

_APP = None


def _app():
    global _APP
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication(["pytest-audit"])
    _APP = app
    return app


class _TicketHolder:
    widget: Any
    upbit: Any
    combo_ticket_symbol: Any
    combo_ticket_type: Any
    spin_ticket_price: Any
    spin_ticket_amount: Any
    chk_ticket_require_confirm: Any
    lbl_ticket_mode: Any
    lbl_ticket_status: Any
    balance: float
    calls: list

    def __init__(self):
        self.balance = 100000.0
        self.calls = []

    def _is_paper_mode(self):
        return True

    def _place_buy_order(self, ticker, amount, source="order_ticket", **kwargs):
        self.calls.append(("BUY", ticker, amount, source))
        return True, {"uuid": "ticket-buy-1"}, ""

    def _place_best_buy_order(self, ticker, amount, source="order_ticket", **kwargs):
        self.calls.append(("BEST-BUY", ticker, amount, source))
        return True, {"uuid": "ticket-best-buy-1"}, ""

    def _place_sell_order(self, ticker, qty, source="order_ticket", **kwargs):
        self.calls.append(("SELL", ticker, qty, source))
        return True, {"uuid": "ticket-sell-1"}, ""

    def _place_best_sell_order(self, ticker, qty, source="order_ticket", **kwargs):
        self.calls.append(("BEST-SELL", ticker, qty, source))
        return True, {"uuid": "ticket-sell-1"}, ""


def _ticket_holder(kind="시장가", price=0.0, amount=10000.0):
    _app()
    holder = _TicketHolder()
    holder.widget = order_ticket_ops.build_order_ticket(holder)
    holder.chk_ticket_require_confirm.setChecked(False)
    holder.combo_ticket_symbol.setCurrentText("KRW-BTC")
    holder.combo_ticket_type.setCurrentText(kind)
    holder.spin_ticket_price.setValue(price)
    holder.spin_ticket_amount.setValue(amount)
    return holder


def _ticket_status(holder):
    return holder.lbl_ticket_status.text()


def test_ticket_market_buy_routes_to_market_order():
    holder = _ticket_holder(kind="시장가")
    assert order_ticket_ops.submit_ticket_order(holder, "BUY") is True
    assert holder.calls[0][0] == "BUY"


def test_ticket_best_buy_routes_to_best_order():
    holder = _ticket_holder(kind="최유리")
    assert order_ticket_ops.submit_ticket_order(holder, "BUY") is True
    assert holder.calls[0][0] == "BEST-BUY"


def test_ticket_best_sell_routes_to_best_order():
    holder = _ticket_holder(kind="최유리")
    assert order_ticket_ops.submit_ticket_order(holder, "SELL") is True
    assert holder.calls[0][0] == "BEST-SELL"


def test_ticket_limit_buy_is_blocked_not_market():
    holder = _ticket_holder(kind="지정가", price=90000.0)
    assert order_ticket_ops.submit_ticket_order(holder, "BUY") is False
    assert holder.calls == []
    assert "미지원" in _ticket_status(holder)


def test_ticket_zero_amount_is_rejected():
    holder = _ticket_holder(kind="시장가", amount=0.0)
    assert order_ticket_ops.submit_ticket_order(holder, "BUY") is False
    assert holder.calls == []


def test_ticket_dry_run_validates_both_sides():
    _app()
    seen = []

    class _Upbit:
        def test_order(self, market, side, volume, price, ord_type):
            seen.append((side, ord_type, volume, price))
            return {"uuid": "test-ok", "market": market}

    holder = _TicketHolder()
    holder.upbit = _Upbit()
    holder.widget = order_ticket_ops.build_order_ticket(holder)
    holder.combo_ticket_symbol.setCurrentText("KRW-BTC")
    holder.combo_ticket_type.setCurrentText("시장가")
    holder.spin_ticket_amount.setValue(5000)
    assert order_ticket_ops.ticket_dry_run(holder) is True
    sides = {side for side, _, _, _ in seen}
    assert sides == {"bid", "ask"}


def test_ticket_dry_run_uses_market_payload_for_sell_leg():
    _app()
    seen = []

    class _Upbit:
        def test_order(self, market, side, volume, price, ord_type):
            seen.append((side, ord_type, volume, price))
            return {"uuid": "test-ok", "market": market}

    holder = _TicketHolder()
    holder.upbit = _Upbit()
    holder.widget = order_ticket_ops.build_order_ticket(holder)
    holder.combo_ticket_symbol.setCurrentText("KRW-BTC")
    holder.combo_ticket_type.setCurrentText("시장가")
    holder.spin_ticket_amount.setValue(5000)
    assert order_ticket_ops.ticket_dry_run(holder) is True
    ask = next(row for row in seen if row[0] == "ask")
    assert ask[1] == "market"
    assert ask[2] == 5000


def test_ticket_dry_run_fails_when_sell_leg_fails():
    _app()

    class _Upbit:
        def test_order(self, market, side, volume, price, ord_type):
            if side == "ask":
                raise RuntimeError("sell not allowed")
            return {"uuid": "test-ok", "market": market}

    holder = _TicketHolder()
    holder.upbit = _Upbit()
    holder.widget = order_ticket_ops.build_order_ticket(holder)
    holder.combo_ticket_symbol.setCurrentText("KRW-BTC")
    holder.combo_ticket_type.setCurrentText("시장가")
    holder.spin_ticket_amount.setValue(5000)
    assert order_ticket_ops.ticket_dry_run(holder) is False


def test_history_save_is_atomic_and_roundtrips(tmp_path, monkeypatch):
    _app()
    from upbit_autotrader.controllers.history_controller import TraderHistoryController

    target = tmp_path / "trade_history.json"
    monkeypatch.setattr(Config, "TRADE_HISTORY_FILE", str(target))
    host = SimpleNamespace(
        trade_history=[{"ticker": "KRW-BTC", "type": "BUY"}],
        _history_dirty=True,
        log=lambda *args: None,
    )
    assert TraderHistoryController._save_trade_history_now(host) is True  # type: ignore[arg-type]
    assert json.loads(target.read_text(encoding="utf-8")) == host.trade_history
    assert not os.path.exists(str(target) + ".tmp")


def test_history_save_failure_keeps_dirty_for_retry(monkeypatch):
    from upbit_autotrader.controllers.history_controller import TraderHistoryController

    monkeypatch.setattr(
        "upbit_autotrader.services.atomic_file.write_json_atomic", lambda *a: False
    )
    host = SimpleNamespace(
        trade_history=[{"ticker": "KRW-BTC"}],
        _history_dirty=False,
        log=lambda *args: None,
    )
    assert TraderHistoryController._save_trade_history_now(host) is False  # type: ignore[arg-type]
    assert host._history_dirty is True


def test_history_corrupt_load_is_backed_up(tmp_path, monkeypatch):
    _app()
    from upbit_autotrader.controllers.history_controller import TraderHistoryController

    target = tmp_path / "trade_history.json"
    target.write_text("{corrupt", encoding="utf-8")
    monkeypatch.setattr(Config, "TRADE_HISTORY_FILE", str(target))
    host = SimpleNamespace(
        trade_history=[{"old": True}],
        _history_dirty=False,
        _history_flush_timer=SimpleNamespace(),
    )
    host._ensure_history_flush_state = (
        TraderHistoryController._ensure_history_flush_state.__get__(host)
    )
    TraderHistoryController.load_trade_history(host)  # type: ignore[arg-type]
    assert host.trade_history == []
    backups = list(tmp_path.glob("trade_history.json.corrupt-*.bak"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{corrupt"


def test_settings_save_survives_dpapi_failure(tmp_path, monkeypatch):
    from upbit_autotrader.services import settings_store
    from upbit_autotrader.services.security import DPAPIError

    def _boom(_text):
        raise DPAPIError("DPAPI is only available on Windows.")

    monkeypatch.setattr(settings_store, "encrypt_dpapi", _boom)
    target = str(tmp_path / "settings.json")
    err = settings_store.save_settings(
        target, {"access_key": "AK", "secret_key": "SK", "k": 0.4}
    )
    assert err
    data = json.loads(Path(target).read_text(encoding="utf-8"))
    assert data["k"] == 0.4
    assert data["api_credentials"]["access_enc"] == ""
    assert "access_key" not in data
    loaded = settings_store.load_settings(target)
    assert loaded["access_key"] == ""
    assert loaded["_credential_error"]


def test_settings_save_returns_none_without_keys(tmp_path):
    from upbit_autotrader.services import settings_store

    target = str(tmp_path / "settings.json")
    assert settings_store.save_settings(target, {"k": 0.4}) is None
    assert json.loads(Path(target).read_text(encoding="utf-8"))["k"] == 0.4


def test_startup_registry_noop_without_winreg(monkeypatch):
    from upbit_autotrader.controllers import settings_controller

    monkeypatch.setattr(settings_controller, "_get_winreg", lambda: None)
    logged = []
    host = SimpleNamespace(log=logged.append)
    settings_controller.TraderSettingsController.set_startup_registry(
        host, True  # type: ignore[arg-type]
    )
    assert logged and "Windows" in logged[0]


def test_file_opener_never_raises(tmp_path):
    from upbit_autotrader.ui.file_opener import open_local_path

    assert open_local_path(str(tmp_path / "missing.html")) is False


def test_qt_binding_guard_rejects_foreign_binding():
    from upbit_autotrader.ui import qt_compat

    try:
        from PySide6.QtWidgets import QWidget as ForeignWidget
    except ImportError:
        ForeignWidget = None
    if ForeignWidget is not None:
        assert qt_compat.is_pyqt6_widget_class(ForeignWidget) is False

    from PyQt6.QtWidgets import QMainWindow

    assert qt_compat.is_pyqt6_widget_class(QMainWindow) is True
    base = qt_compat.fluent_window_base()
    assert base is None or qt_compat.is_pyqt6_widget_class(base)


def test_trader_window_is_pyqt6_object():
    _app()
    from PyQt6.QtCore import QObject

    from upbit_autotrader.app.trader import UpbitProTrader

    assert issubclass(UpbitProTrader, QObject)


def test_validate_live_order_request_blocks_halted_market():
    from upbit_autotrader.controllers.trading_parts.execution.validation import (
        _validate_live_order_request,
    )

    host = SimpleNamespace(
        _is_paper_mode=lambda: False,
        _api_get_order_chance=lambda ticker: {
            "market": {
                "state": "halt",
                "bid_types": ["price"],
                "ask_types": ["market"],
                "bid": {"min_total": 5000.0},
            }
        },
    )
    ok, err, _chance = _validate_live_order_request(host, "KRW-BTC", "BUY", notional_krw=6000.0)
    assert ok is False
    assert err
