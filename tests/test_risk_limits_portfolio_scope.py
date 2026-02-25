from upbit_order_service import UpbitOrderService
from upbit_trader_trading_controller import TraderTradingController


class _Check:
    def __init__(self, checked):
        self._checked = checked

    def isChecked(self):
        return self._checked


class _Spin:
    def __init__(self, value):
        self._value = value

    def value(self):
        return self._value


class _DummyLogger:
    def info(self, *_):
        return None

    def warning(self, *_):
        return None

    def error(self, *_):
        return None


class _RiskTrader(TraderTradingController):
    def __init__(self, universe, external_holdings, realized_pnl=0.0, initial_balance=1_000_000.0, max_holdings=5):
        self.order_service = UpbitOrderService()
        self.pending_orders = self.order_service.pending_orders
        self.universe = dict(universe)
        self.external_holdings = list(external_holdings)
        self.total_realized_profit = float(realized_pnl)
        self.initial_balance = float(initial_balance)
        self.daily_loss_triggered = False
        self.chk_use_risk = _Check(True)
        self.spin_max_loss = _Spin(5.0)
        self.spin_max_holdings = _Spin(max_holdings)
        self.chk_risk_include_unrealized = _Check(True)
        self.chk_risk_include_external_holdings = _Check(True)
        self.chk_enable_account_wide_sync = _Check(True)
        self.logger = _DummyLogger()

    def get_account_holdings(self):
        return list(self.external_holdings)

    def log(self, *_):
        return None


def test_risk_limits_blocks_entry_when_unrealized_loss_overwhelms_realized_gain():
    trader = _RiskTrader(
        universe={
            "KRW-BTC": {
                "qty": 1.0,
                "buy_price": 1_000_000.0,
                "current": 800_000.0,
            }
        },
        external_holdings=[],
        realized_pnl=50_000.0,
        initial_balance=1_000_000.0,
        max_holdings=5,
    )

    assert trader.check_risk_limits() is False
    assert trader.daily_loss_triggered is True


def test_risk_limits_uses_account_wide_holdings_count_for_limit():
    trader = _RiskTrader(
        universe={
            "KRW-BTC": {
                "qty": 0.5,
                "buy_price": 1000.0,
                "current": 1000.0,
            }
        },
        external_holdings=[
            {
                "ticker": "KRW-ETH",
                "qty": 1.0,
                "buy_price": 2000.0,
                "current_price": 2000.0,
                "value": 2000.0,
            }
        ],
        realized_pnl=0.0,
        initial_balance=1_000_000.0,
        max_holdings=2,
    )

    snapshot = trader._get_risk_snapshot(force=True)
    assert int(snapshot.get("holdings_count", 0)) == 2
    assert trader.check_risk_limits() is False
