"""
Upbit Backtester v1.0
백테스팅 엔진 for Upbit Pro Algo-Trader

변동성 돌파 전략 등 다양한 전략의 과거 성과 분석
"""

import pyupbit
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional, Any
from datetime import datetime, timedelta
import json



def volatility_breakout_strategy(df: pd.DataFrame, i: int, k: float = 0.4) -> str:
    """변동성 돌파 전략"""
    if i < 2:
        return 'HOLD'
    
    prev_range = df['high'].iloc[i-1] - df['low'].iloc[i-1]
    target = df['open'].iloc[i] + prev_range * k
    current = df['close'].iloc[i]
    
    if current > target:
        return 'BUY'
    return 'HOLD'


def ma_crossover_strategy(df: pd.DataFrame, i: int, 
                          short: int = 5, long: int = 20) -> str:
    """이동평균 크로스오버 전략"""
    if i < long:
        return 'HOLD'
    
    ma_short = df['close'].iloc[i-short:i+1].mean()
    ma_long = df['close'].iloc[i-long:i+1].mean()
    
    ma_short_prev = df['close'].iloc[i-short-1:i].mean()
    ma_long_prev = df['close'].iloc[i-long-1:i].mean()
    
    # 골든크로스
    if ma_short > ma_long and ma_short_prev <= ma_long_prev:
        return 'BUY'
    # 데드크로스
    elif ma_short < ma_long and ma_short_prev >= ma_long_prev:
        return 'SELL'
    
    return 'HOLD'


def donchian_breakout_strategy(df: pd.DataFrame, i: int, period: int = 20) -> str:
    if i < period + 1:
        return 'HOLD'
    upper = df['high'].iloc[i-period:i].max()
    lower = df['low'].iloc[i-period:i].min()
    current = df['close'].iloc[i]
    if current > upper:
        return 'BUY'
    if current < lower:
        return 'SELL'
    return 'HOLD'


def ema_cross_trend_strategy(df: pd.DataFrame, i: int, fast: int = 12, slow: int = 26) -> str:
    if i < slow + 2:
        return 'HOLD'
    close = df['close'].iloc[: i + 1]
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    if ema_fast.iloc[-1] > ema_slow.iloc[-1] and ema_fast.iloc[-2] <= ema_slow.iloc[-2]:
        return 'BUY'
    if ema_fast.iloc[-1] < ema_slow.iloc[-1] and ema_fast.iloc[-2] >= ema_slow.iloc[-2]:
        return 'SELL'
    return 'HOLD'


def time_series_momentum_strategy(df: pd.DataFrame, i: int, lookback: int = 20, threshold_pct: float = 1.0) -> str:
    if i < lookback:
        return 'HOLD'
    base = df['close'].iloc[i - lookback]
    if base <= 0:
        return 'HOLD'
    ret = (df['close'].iloc[i] - base) / base * 100.0
    if ret >= threshold_pct:
        return 'BUY'
    if ret <= -threshold_pct:
        return 'SELL'
    return 'HOLD'


def rsi_reversion_strategy(df: pd.DataFrame, i: int, period: int = 14, oversold: float = 30, exit_rsi: float = 55) -> str:
    if i < period + 2:
        return 'HOLD'
    close = df['close'].iloc[: i + 1]
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    current_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
    if current_rsi <= oversold:
        return 'BUY'
    if current_rsi >= exit_rsi:
        return 'SELL'
    return 'HOLD'


def bollinger_reversion_strategy(df: pd.DataFrame, i: int, period: int = 20, std_mult: float = 2.0) -> str:
    if i < period + 2:
        return 'HOLD'
    close = df['close'].iloc[: i + 1]
    ma = close.rolling(window=period).mean().iloc[-1]
    std = close.rolling(window=period).std().iloc[-1]
    if pd.isna(ma) or pd.isna(std) or std == 0:
        return 'HOLD'
    lower = ma - std_mult * std
    current = close.iloc[-1]
    if current <= lower:
        return 'BUY'
    if current >= ma:
        return 'SELL'
    return 'HOLD'


def zscore_reversion_strategy(df: pd.DataFrame, i: int, period: int = 20, entry_z: float = -1.8, exit_z: float = -0.3) -> str:
    if i < period + 2:
        return 'HOLD'
    close = df['close'].iloc[: i + 1]
    ma = close.rolling(window=period).mean().iloc[-1]
    std = close.rolling(window=period).std().iloc[-1]
    if pd.isna(ma) or pd.isna(std) or std == 0:
        return 'HOLD'
    z = (close.iloc[-1] - ma) / std
    if z <= entry_z:
        return 'BUY'
    if z >= exit_z:
        return 'SELL'
    return 'HOLD'


def ensemble_basic_strategy(df: pd.DataFrame, i: int, threshold: int = 2) -> str:
    votes = [
        volatility_breakout_strategy(df, i),
        ema_cross_trend_strategy(df, i),
        time_series_momentum_strategy(df, i),
        rsi_reversion_strategy(df, i),
        bollinger_reversion_strategy(df, i),
        zscore_reversion_strategy(df, i),
    ]
    buy_votes = sum(1 for v in votes if v == 'BUY')
    sell_votes = sum(1 for v in votes if v == 'SELL')
    if buy_votes >= threshold and buy_votes > sell_votes:
        return 'BUY'
    if sell_votes >= threshold and sell_votes > buy_votes:
        return 'SELL'
    return 'HOLD'
