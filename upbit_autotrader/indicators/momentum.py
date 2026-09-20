"""
Upbit Advanced Indicators v1.0
고급 기술지표 모듈 for Upbit Pro Algo-Trader

Williams %R, CCI, OBV, Ichimoku Cloud, Pivot Points, Parabolic SAR
"""

import pyupbit
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Any,  Optional, Tuple, List, Dict
from datetime import datetime


class MomentumIndicatorsMixin:
    """Momentum oscillators: Williams %R, CCI (SRP)."""

    get_ohlcv: Any

    def calculate_williams_r(self, ticker: str, period: int = 14) -> Optional[float]:
        """
        Williams %R 계산 (-100 ~ 0)
        -80 이하: 과매도, -20 이상: 과매수
        """
        df = self.get_ohlcv(ticker, count=period + 5)
        if df.empty or len(df) < period:
            return None
            
        high_max = df['high'].rolling(window=period).max()
        low_min = df['low'].rolling(window=period).min()
        close = df['close']
        
        wr = -100 * (high_max - close) / (high_max - low_min)
        wr_series = pd.Series(wr)
        wr_value = wr_series.iloc[-1]
        return float(wr_value)

    def check_williams_r_condition(self, ticker: str, period: int = 14,
                                   oversold: float = -80, 
                                   overbought: float = -20) -> Tuple[str, float]:
        """
        Williams %R 조건 확인
        Returns: (signal, value)
            signal: 'BUY', 'SELL', 'NEUTRAL'
        """
        wr = self.calculate_williams_r(ticker, period)
        if wr is None:
            return 'NEUTRAL', 0.0
            
        if wr <= oversold:
            return 'BUY', wr
        elif wr >= overbought:
            return 'SELL', wr
        else:
            return 'NEUTRAL', wr

    def calculate_cci(self, ticker: str, period: int = 20) -> Optional[float]:
        """
        CCI 계산
        +100 이상: 과매수, -100 이하: 과매도
        """
        df = self.get_ohlcv(ticker, count=period + 10)
        if df.empty or len(df) < period:
            return None
            
        tp = (df['high'] + df['low'] + df['close']) / 3  # Typical Price
        sma = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        
        cci = (tp - sma) / (0.015 * mad)
        return float(cci.iloc[-1])

    def check_cci_condition(self, ticker: str, period: int = 20,
                           overbought: float = 100, 
                           oversold: float = -100) -> Tuple[str, float]:
        """CCI 조건 확인"""
        cci = self.calculate_cci(ticker, period)
        if cci is None:
            return 'NEUTRAL', 0.0
            
        if cci <= oversold:
            return 'BUY', cci
        elif cci >= overbought:
            return 'SELL', cci
        else:
            return 'NEUTRAL', cci
