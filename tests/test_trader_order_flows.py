from unittest.mock import patch

from PyQt6.QtWidgets import QMessageBox

from upbit_order_service import UpbitOrderService
from upbit_trader_batch_controller import TraderBatchController
from upbit_trader_trading_controller import TraderTradingController


class _DummyLabel:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


class _DummyTable:
    def setItem(self, *args, **kwargs):
        return None


class _DummyLogger:
    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None


class _FakeUpbitOrders:
    def __init__(self, order_map):
        self.order_map = order_map

    def get_order(self, uuid):
        return self.order_map.get(uuid, {"state": "wait"})


class _FakeUpbitSell:
    def __init__(self):
        self.sell_seq = 0

    def sell_market_order(self, ticker, qty):
        self.sell_seq += 1
        return {"uuid": f"sell-{self.sell_seq}"}


class _FakeTraderCore:
    def __init__(self, upbit):
        self.upbit = upbit
        self.order_service = UpbitOrderService()
        self.universe = {}
        self.table = _DummyTable()
        self.logger = _DummyLogger()
        self.lbl_total_profit = _DummyLabel()
        self.total_realized_profit = 0.0
        self.trade_count = 0
        self.win_count = 0
        self.strategy = None
        self.log_messages = []

    def set_table_item(self, *args, **kwargs):
        return None

    def log(self, msg):
        self.log_messages.append(msg)

    def add_trade_record(self, *args, **kwargs):
        return None

    def get_balance(self):
        return None

    def _update_statistics(self):
        return None


def test_check_buy_execution_clears_pending_done_cancel_timeout():
    ticker = "KRW-BTC"

    # done
    done_order = {
        "state": "done",
        "executed_volume": "0.01",
        "paid_fee": "100",
        "trades": [{"price": "50000000", "volume": "0.01"}],
    }
    trader = _FakeTraderCore(_FakeUpbitOrders({"buy-done": done_order}))
    trader.universe[ticker] = {"row": 0, "state": "주문중", "qty": 0, "buy_price": 0, "invest_amt": 0}
    trader.order_service.mark_pending(ticker, "BUY", "buy-done")
    TraderTradingController.check_buy_execution(trader, ticker, "buy-done")
    assert not trader.order_service.has_pending(ticker)
    assert trader.universe[ticker]["state"] == "보유중"
    assert trader.universe[ticker]["qty"] > 0

    # cancel
    cancel_trader = _FakeTraderCore(_FakeUpbitOrders({"buy-cancel": {"state": "cancel"}}))
    cancel_trader.universe[ticker] = {"row": 0, "state": "주문중", "qty": 0}
    cancel_trader.order_service.mark_pending(ticker, "BUY", "buy-cancel")
    TraderTradingController.check_buy_execution(cancel_trader, ticker, "buy-cancel")
    assert not cancel_trader.order_service.has_pending(ticker)
    assert cancel_trader.universe[ticker]["state"] == "감시중"

    # timeout path
    timeout_trader = _FakeTraderCore(_FakeUpbitOrders({"buy-timeout": {"state": "wait"}}))
    timeout_trader.universe[ticker] = {"row": 0, "state": "주문중", "qty": 0}
    timeout_trader.order_service.mark_pending(ticker, "BUY", "buy-timeout")
    TraderTradingController.check_buy_execution(timeout_trader, ticker, "buy-timeout", retry_count=30)
    assert not timeout_trader.order_service.has_pending(ticker)
    assert timeout_trader.universe[ticker]["state"] == "체결확인실패"


def test_check_sell_execution_clears_pending_done_cancel_timeout():
    ticker = "KRW-ETH"

    # done
    done_order = {
        "state": "done",
        "executed_volume": "1",
        "executed_funds": "12000",
        "paid_fee": "10",
        "trades": [],
    }
    trader = _FakeTraderCore(_FakeUpbitOrders({"sell-done": done_order}))
    trader.universe[ticker] = {"row": 0, "state": "매도주문중", "qty": 1.0, "invest_amt": 10000.0}
    trader.order_service.mark_pending(ticker, "SELL", "sell-done")
    TraderTradingController.check_sell_execution(trader, ticker, "sell-done", "테스트매도")
    assert not trader.order_service.has_pending(ticker)
    assert trader.universe[ticker]["state"] == "매도완료"
    assert trader.universe[ticker]["qty"] == 0

    # cancel
    cancel_trader = _FakeTraderCore(_FakeUpbitOrders({"sell-cancel": {"state": "cancel"}}))
    cancel_trader.universe[ticker] = {"row": 0, "state": "매도주문중", "qty": 0.5, "invest_amt": 5000.0}
    cancel_trader.order_service.mark_pending(ticker, "SELL", "sell-cancel")
    TraderTradingController.check_sell_execution(cancel_trader, ticker, "sell-cancel", "테스트매도")
    assert not cancel_trader.order_service.has_pending(ticker)
    assert cancel_trader.universe[ticker]["state"] == "보유중"

    # timeout path
    timeout_trader = _FakeTraderCore(_FakeUpbitOrders({"sell-timeout": {"state": "wait"}}))
    timeout_trader.universe[ticker] = {"row": 0, "state": "매도주문중", "qty": 0.5, "invest_amt": 5000.0}
    timeout_trader.order_service.mark_pending(ticker, "SELL", "sell-timeout")
    TraderTradingController.check_sell_execution(
        timeout_trader, ticker, "sell-timeout", "테스트매도", retry_count=30
    )
    assert not timeout_trader.order_service.has_pending(ticker)
    assert timeout_trader.universe[ticker]["state"] == "체결확인실패"


class _FakeCheck:
    def isChecked(self):
        return False


class _FakeBatchTrader:
    def __init__(self):
        self.upbit = _FakeUpbitSell()
        self.order_service = UpbitOrderService()
        self.universe = {"KRW-BTC": {"qty": 0.2, "state": "보유중", "row": 0}}
        self.logger = _DummyLogger()
        self.chk_auto_start_after_batch = _FakeCheck()
        self.logs = []
        self.internal_sell_calls = []
        self.external_sell_checks = []
        self.internal_sell_checks = []

    def log(self, msg):
        self.logs.append(msg)

    def get_balance(self):
        return None

    def start_trading(self):
        return None

    def set_table_item(self, *args, **kwargs):
        return None

    def get_account_holdings(self):
        return [
            {"ticker": "KRW-BTC", "qty": 0.2, "value": 10000.0},
            {"ticker": "KRW-XRP", "qty": 100.0, "value": 15000.0},
        ]

    def execute_sell(self, ticker, reason):
        self.internal_sell_calls.append((ticker, reason))
        self.order_service.mark_pending(ticker, "SELL", "internal-uuid")

    def _check_external_sell_execution(self, ticker, uuid, reason="외부매도", context_label="외부 매도", retry_count=0):
        self.external_sell_checks.append((ticker, uuid, reason, context_label, retry_count))
        self.order_service.clear_pending(ticker)

    def check_sell_execution(self, ticker, uuid, reason, retry_count=0):
        self.internal_sell_checks.append((ticker, uuid, reason, retry_count))
        self.order_service.clear_pending(ticker)


def test_batch_sell_routes_universe_and_external_paths():
    trader = _FakeBatchTrader()

    with patch(
        "upbit_trader_batch_controller.QMessageBox.warning",
        return_value=QMessageBox.StandardButton.Yes,
    ), patch(
        "upbit_trader_batch_controller.QInputDialog.getText",
        return_value=("2", True),
    ), patch(
        "upbit_trader_batch_controller.QTimer.singleShot",
        side_effect=lambda _ms, cb: cb(),
    ):
        TraderBatchController.execute_batch_sell(trader)

    assert trader.internal_sell_calls == [("KRW-BTC", "일괄매도")]
    assert len(trader.external_sell_checks) == 1
    assert trader.external_sell_checks[0][0] == "KRW-XRP"


def test_emergency_close_routes_universe_and_external_paths():
    trader = _FakeBatchTrader()

    with patch(
        "upbit_trader_batch_controller.QTimer.singleShot",
        side_effect=lambda _ms, cb: cb(),
    ):
        TraderBatchController.execute_emergency_close(trader)

    assert len(trader.internal_sell_checks) == 1
    assert trader.internal_sell_checks[0][0] == "KRW-BTC"
    assert len(trader.external_sell_checks) == 1
    assert trader.external_sell_checks[0][0] == "KRW-XRP"
