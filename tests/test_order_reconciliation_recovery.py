from upbit_order_service import UpbitOrderService
from upbit_trader_trading_controller import TraderTradingController


class _Check:
    def __init__(self, checked):
        self._checked = checked

    def isChecked(self):
        return self._checked


class _DummyLogger:
    def info(self, *_):
        return None

    def warning(self, *_):
        return None

    def error(self, *_):
        return None


class _FakeUpbit:
    def __init__(self, order_map=None):
        self.order_map = order_map or {}
        self.cancel_calls = []

    def get_order(self, uuid):
        return self.order_map.get(uuid, {"state": "wait"})

    def cancel_order(self, uuid):
        self.cancel_calls.append(uuid)
        return {"uuid": uuid, "state": "cancel"}


class _Trader(TraderTradingController):
    def __init__(self, order_map=None):
        self.upbit = _FakeUpbit(order_map)
        self.order_service = UpbitOrderService()
        self.pending_orders = self.order_service.pending_orders
        self.universe = {}
        self.logger = _DummyLogger()
        self.chk_manual_review_on_timeout = _Check(True)
        self.chk_paper_trading = _Check(False)
        self._sync_count = 0
        self._external_buy_done = 0
        self._reserved_krw_by_ticker = {}

    def log(self, *_):
        return None

    def _check_external_buy_execution(self, ticker, uuid, **_):
        self._external_buy_done += 1
        self.order_service.clear_pending(ticker)

    def _sync_account_holdings_to_universe(self, account_holdings=None, include_external=None):
        self._sync_count += 1


def test_timeout_reconcile_handles_terminal_done_and_clears_pending():
    trader = _Trader(
        {
            "buy-timeout-done": {
                "state": "done",
                "executed_volume": "1",
                "trades": [{"price": "1000", "volume": "1"}],
                "paid_fee": "0",
            }
        }
    )
    trader.order_service.mark_pending("KRW-XRP", "BUY", "buy-timeout-done")

    pending = trader.order_service.get_pending("KRW-XRP")
    resolved = trader._resolve_timeout_pending("KRW-XRP", pending, reason="unit_timeout")

    assert resolved is True
    assert trader._external_buy_done == 1
    assert not trader.order_service.has_pending("KRW-XRP")


def test_timeout_reconcile_unresolved_moves_to_manual_review_queue():
    trader = _Trader({"buy-timeout-wait": {"state": "wait"}})
    trader.order_service.mark_pending("KRW-BTC", "BUY", "buy-timeout-wait")

    pending = trader.order_service.get_pending("KRW-BTC")
    resolved = trader._resolve_timeout_pending("KRW-BTC", pending, reason="unit_timeout_wait")

    assert resolved is False
    assert trader.order_service.has_pending("KRW-BTC")
    pending_after = trader.order_service.get_pending("KRW-BTC")
    assert pending_after is not None
    assert pending_after.get("needs_manual_review") is True
    assert pending_after.get("lifecycle_state") == "manual_review"
    assert trader._manual_review_queue


def test_session_mismatch_done_registers_orphan_and_reconciles_state():
    trader = _Trader()
    trader._active_session_id = 2
    trader._reserved_krw_by_ticker["KRW-ETH"] = 5000.0
    trader.order_service.mark_pending("KRW-ETH", "BUY", "buy-stale", session_id=1)

    trader._handle_session_mismatch_terminal(
        ticker="KRW-ETH",
        uuid="buy-stale",
        side="BUY",
        state="done",
        session_id=1,
        source="unit_test",
    )

    assert not trader.order_service.has_pending("KRW-ETH")
    assert trader._sync_count == 1
    assert len(trader._orphan_events) == 1
    assert trader._orphan_events[0]["uuid"] == "buy-stale"
