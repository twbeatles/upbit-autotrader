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


class VolumeIndicatorsMixin:
    """Volume responsibility: OBV (SRP)."""

    get_ohlcv: Any

    def calculate_obv(self, ticker: str, count: int = 50) -> Optional[List[float]]:
        """OBV 계산"""
        df = self.get_ohlcv(ticker, count=count)
        if df.empty or len(df) < 2:
            return None
            
        obv: List[float] = [0.0]
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.append(float(obv[-1] + float(df['volume'].iloc[i])))
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.append(float(obv[-1] - float(df['volume'].iloc[i])))
            else:
                obv.append(float(obv[-1]))
        return obv

    def calculate_obv_signal(self, ticker: str, period: int = 20) -> Tuple[str, float]:
        """
        OBV 신호 (OBV 이동평균 대비)
        Returns: ('BULLISH'/'BEARISH'/'NEUTRAL', obv_ratio)
        """
        obv = self.calculate_obv(ticker, period + 10)
        if not obv or len(obv) < period:
            return 'NEUTRAL', 0.0
            
        obv_series = pd.Series(obv)
        obv_ma = obv_series.rolling(window=period).mean()
        obv_ma_values = list(obv_ma)
        
        current = obv[-1]
        ma = float(obv_ma_values[-1])
        
        if ma == 0:
            return 'NEUTRAL', 0.0
            
        ratio = (current - ma) / abs(ma) * 100
        
        if ratio > 5:
            return 'BULLISH', ratio
        elif ratio < -5:
            return 'BEARISH', ratio
        else:
            return 'NEUTRAL', ratio
