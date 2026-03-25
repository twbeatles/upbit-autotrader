from __future__ import annotations

from typing import Any, cast

from upbit_autotrader.controllers.trading_parts.indicator_parts import cache_ops, compute_ops, snapshot_ops

# Runtime bindings injected by trading_controller facade
Config = cast(Any, None)
pd = cast(Any, None)
pyupbit = cast(Any, None)
time = cast(Any, None)


def bind_runtime(**kwargs):
    globals().update(kwargs)
    cache_ops.bind_runtime(**kwargs)
    compute_ops.bind_runtime(**kwargs)
    snapshot_ops.bind_runtime(**kwargs)



def calculate_target_price(self, ticker, interval):
    return compute_ops.calculate_target_price(self, ticker, interval)


def calculate_ma(self, ticker, interval, period=5):
    return compute_ops.calculate_ma(self, ticker, interval, period)


def calculate_rsi(self, ticker, period=14):
    return snapshot_ops.calculate_rsi(self, ticker, period)


def calculate_macd(self, ticker):
    return snapshot_ops.calculate_macd(self, ticker)


def calculate_bollinger_bands(self, ticker):
    return snapshot_ops.calculate_bollinger_bands(self, ticker)


def calculate_atr(self, ticker, period=14):
    return compute_ops.calculate_atr(self, ticker, period)


def calculate_volume_avg(self, ticker, period=20):
    return snapshot_ops.calculate_volume_avg(self, ticker, period)


def calculate_stoch_rsi(self, ticker, rsi_period=14, stoch_period=14, k_period=3, d_period=3):
    return compute_ops.calculate_stoch_rsi(self, ticker, rsi_period, stoch_period, k_period, d_period)


def calculate_dmi_adx(self, ticker, period=14):
    return compute_ops.calculate_dmi_adx(self, ticker, period)


def _get_indicator_cache_ttl(self, interval):
    return cache_ops._get_indicator_cache_ttl(self, interval)


def _compute_rsi_from_close(self, close, period):
    return compute_ops._compute_rsi_from_close(close, period)


def _get_indicator_snapshot(self, ticker, interval, rsi_period=None, volume_period=None, bb_period=None):
    return snapshot_ops._get_indicator_snapshot(self, ticker, interval, rsi_period, volume_period, bb_period)
