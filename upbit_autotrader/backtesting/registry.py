"""Strategy registry (OCP: new strategies register without modifying engine)."""
from __future__ import annotations

from typing import Any, Dict

from .strategies import (
    bollinger_reversion_strategy,
    donchian_breakout_strategy,
    ema_cross_trend_strategy,
    ensemble_basic_strategy,
    ma_crossover_strategy,
    rsi_reversion_strategy,
    time_series_momentum_strategy,
    volatility_breakout_strategy,
    zscore_reversion_strategy,
)

STRATEGY_REGISTRY: Dict[str, Dict[str, Any]] = {
    "volatility_breakout": {"name": "변동성 돌파", "func": volatility_breakout_strategy, "params": {"k": 0.4}},
    "ma_crossover": {"name": "MA 크로스오버", "func": ma_crossover_strategy, "params": {"short": 5, "long": 20}},
    "donchian_breakout": {"name": "돈치안 돌파", "func": donchian_breakout_strategy, "params": {"period": 20}},
    "ema_cross_trend": {"name": "EMA 크로스", "func": ema_cross_trend_strategy, "params": {"fast": 12, "slow": 26}},
    "time_series_momentum": {"name": "시계열 모멘텀", "func": time_series_momentum_strategy, "params": {"lookback": 20, "threshold_pct": 1.0}},
    "rsi_reversion": {"name": "RSI 평균회귀", "func": rsi_reversion_strategy, "params": {"period": 14, "oversold": 30, "exit_rsi": 55}},
    "bollinger_reversion": {"name": "볼린저 평균회귀", "func": bollinger_reversion_strategy, "params": {"period": 20, "std_mult": 2.0}},
    "zscore_reversion": {"name": "Z-Score 평균회귀", "func": zscore_reversion_strategy, "params": {"period": 20, "entry_z": -1.8, "exit_z": -0.3}},
    "ensemble_basic": {"name": "앙상블(기본)", "func": ensemble_basic_strategy, "params": {"threshold": 2}},
}


def get_strategy_registry() -> Dict[str, Dict[str, Any]]:
    return dict(STRATEGY_REGISTRY)
