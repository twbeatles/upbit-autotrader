from upbit_strategy_engine import StrategyEngine, StrategyConfig


class _Spin:
    def __init__(self, v):
        self._v = v

    def value(self):
        return self._v


class _Strategy:
    consecutive_losses = 0

    def check_mtf_condition(self, *_):
        return True


class _Trader:
    def __init__(self):
        self.spin_regime_min_adx = _Spin(18.0)
        self.spin_drawdown_guard = _Spin(5.0)
        self.spin_max_consecutive_losses = _Spin(3)
        self.spin_target_vol = _Spin(2.0)
        self.initial_balance = 1_000_000
        self.total_realized_profit = 0
        self.strategy = _Strategy()


def test_ensemble_weighted_threshold_passes():
    trader = _Trader()
    engine = StrategyEngine(trader)
    cfg = StrategyConfig(
        enabled=True,
        mode="ensemble",
        ensemble_threshold=60.0,
        active_strategies=["volatility_breakout", "time_series_momentum"],
        weights={"volatility_breakout": 2.0, "time_series_momentum": 1.0},
    )

    info = {"target": 100.0, "ma5": 99.0}
    snapshot = {"ts_momentum_pct": 2.0, "adx": 30.0}
    sig = engine.evaluate_entry("KRW-BTC", 101.0, info, snapshot, cfg)

    assert sig.strategy_id == "ensemble"
    assert sig.action == "BUY"
    assert sig.score >= 60.0


def test_ensemble_weighted_threshold_blocks():
    trader = _Trader()
    engine = StrategyEngine(trader)
    cfg = StrategyConfig(
        enabled=True,
        mode="ensemble",
        ensemble_threshold=80.0,
        active_strategies=["volatility_breakout", "time_series_momentum"],
        weights={"volatility_breakout": 1.0, "time_series_momentum": 1.0},
    )

    info = {"target": 100.0, "ma5": 99.0}
    snapshot = {"ts_momentum_pct": 0.2, "adx": 30.0}
    sig = engine.evaluate_entry("KRW-BTC", 101.0, info, snapshot, cfg)

    assert sig.action == "HOLD"
    assert sig.score < 80.0
