"""Backward-compat shim: implementation lives in split modules (SOLID SRP split)."""
from __future__ import annotations

from upbit_autotrader.backtesting.models import BacktestResult, Trade
from upbit_autotrader.backtesting.engine import UpbitBacktestEngine
from upbit_autotrader.backtesting.strategies import (
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
from upbit_autotrader.backtesting.registry import STRATEGY_REGISTRY, get_strategy_registry

__all__ = ["Trade","BacktestResult","UpbitBacktestEngine","volatility_breakout_strategy","ma_crossover_strategy","donchian_breakout_strategy","ema_cross_trend_strategy","time_series_momentum_strategy","rsi_reversion_strategy","bollinger_reversion_strategy","zscore_reversion_strategy","ensemble_basic_strategy","STRATEGY_REGISTRY","get_strategy_registry"]
