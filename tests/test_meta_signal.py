import datetime

from upbit_autotrader.strategies.meta_signal import (
    MetaSignalInput,
    StrategyPerformanceTracker,
    evaluate_meta_signal,
)


def test_meta_signal_gate_passes_with_positive_expectancy():
    tracker = StrategyPerformanceTracker()
    for pnl in [1.2, 0.8, -0.4, 1.0, 0.9]:
        tracker.update("ema_cross_trend", pnl)

    out = evaluate_meta_signal(
        MetaSignalInput(
            strategy_id="ema_cross_trend",
            engine_score=72.0,
            regime_score=65.0,
            min_expectancy=0.0,
            score_threshold=60.0,
        ),
        tracker=tracker,
    )
    assert out.expected_value > 0
    assert out.meta_score >= 60.0
    assert out.gate_pass


def test_meta_signal_gate_blocks_when_expectancy_negative():
    tracker = StrategyPerformanceTracker()
    for pnl in [-1.5, -0.8, -1.2]:
        tracker.update("rsi_reversion", pnl)

    out = evaluate_meta_signal(
        MetaSignalInput(
            strategy_id="rsi_reversion",
            engine_score=80.0,
            regime_score=70.0,
            min_expectancy=0.0,
            score_threshold=55.0,
        ),
        tracker=tracker,
    )
    assert out.expected_value < 0
    assert not out.gate_pass


def test_weight_rebalance_runs_once_per_day():
    tracker = StrategyPerformanceTracker()
    for pnl in [1.0, 1.1, 0.9]:
        tracker.update("volatility_breakout", pnl)

    changed, w1 = tracker.rebalance_weights_daily(
        {"volatility_breakout": 1.0},
        weight_min=0.5,
        weight_max=1.5,
        ema_alpha=0.2,
        now=datetime.date(2026, 2, 27),
    )
    assert changed
    assert w1["volatility_breakout"] != 1.0

    changed_again, w2 = tracker.rebalance_weights_daily(
        w1,
        weight_min=0.5,
        weight_max=1.5,
        ema_alpha=0.2,
        now=datetime.date(2026, 2, 27),
    )
    assert not changed_again
    assert w2 == w1

