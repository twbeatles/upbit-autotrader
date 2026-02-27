from upbit_autotrader.strategies.engine import StrategyConfig
from upbit_autotrader.controllers.trading_controller import TraderTradingController


class _Combo:
    def __init__(self, value):
        self._value = value

    def currentData(self):
        return self._value


class _Trader(TraderTradingController):
    def __init__(self, policy="strategy_aware"):
        self.combo_engine_gate_policy = _Combo(policy)


def test_strategy_aware_allows_mean_reversion_without_legacy_hard_gate():
    trader = _Trader(policy="strategy_aware")
    cfg = StrategyConfig(enabled=True, mode="single", single_strategy="rsi_reversion")

    assert trader._should_apply_legacy_entry_gate(cfg) is False


def test_strategy_aware_keeps_legacy_hard_gate_for_trend_strategy():
    trader = _Trader(policy="strategy_aware")
    cfg = StrategyConfig(enabled=True, mode="single", single_strategy="volatility_breakout")

    assert trader._should_apply_legacy_entry_gate(cfg) is True


def test_strategy_aware_disables_legacy_hard_gate_for_mixed_ensemble():
    trader = _Trader(policy="strategy_aware")
    cfg = StrategyConfig(
        enabled=True,
        mode="ensemble",
        active_strategies=["volatility_breakout", "rsi_reversion"],
    )

    assert trader._should_apply_legacy_entry_gate(cfg) is False

