from upbit_strategy_engine import StrategyEngine, StrategyConfig


class _DummySpin:
    def __init__(self, v):
        self._v = v

    def value(self):
        return self._v


class _DummyCheck:
    def __init__(self, checked):
        self._checked = checked

    def isChecked(self):
        return self._checked


class _DummyStrategy:
    consecutive_losses = 0

    def check_mtf_condition(self, *_):
        return True


class _DummyTrader:
    def __init__(self):
        self.spin_regime_min_adx = _DummySpin(18.0)
        self.spin_drawdown_guard = _DummySpin(5.0)
        self.spin_max_consecutive_losses = _DummySpin(3)
        self.spin_target_vol = _DummySpin(2.0)
        self.initial_balance = 1_000_000
        self.total_realized_profit = 0.0
        self.strategy = _DummyStrategy()


def test_single_strategy_entry_buy_signal():
    trader = _DummyTrader()
    engine = StrategyEngine(trader)
    cfg = StrategyConfig(enabled=True, mode="single", single_strategy="ema_cross_trend")

    snapshot = {
        "ema_fast": 101.0,
        "ema_slow": 100.0,
        "ema_fast_prev": 99.0,
        "adx": 30.0,
    }
    info = {"target": 100.0, "ma5": 99.0}
    sig = engine.evaluate_entry("KRW-BTC", 102.0, info, snapshot, cfg)

    assert sig.action == "BUY"
    assert sig.score >= 50


def test_mean_reversion_exit_signal():
    trader = _DummyTrader()
    engine = StrategyEngine(trader)
    cfg = StrategyConfig(enabled=True, mode="single", single_strategy="rsi_reversion")

    info = {"target": 0.0, "ma5": 0.0}
    snapshot = {"rsi": 60.0, "adx": 30.0}
    sig = engine.evaluate_exit("KRW-BTC", 100.0, info, snapshot, cfg)

    assert sig.action == "SELL"


def test_drawdown_guard_blocks_entry():
    trader = _DummyTrader()
    trader.total_realized_profit = -100_000  # -10%
    engine = StrategyEngine(trader)
    cfg = StrategyConfig(enabled=True, mode="single", single_strategy="volatility_breakout")

    info = {"target": 90.0, "ma5": 90.0}
    snapshot = {"adx": 30.0}
    sig = engine.evaluate_entry("KRW-BTC", 100.0, info, snapshot, cfg)

    assert sig.action == "HOLD"
    assert sig.strategy_id == "drawdown_guard"
