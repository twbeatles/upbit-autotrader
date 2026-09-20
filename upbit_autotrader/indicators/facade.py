"""
Upbit Advanced Indicators v1.0
고급 기술지표 모듈 for Upbit Pro Algo-Trader

Williams %R, CCI, OBV, Ichimoku Cloud, Pivot Points, Parabolic SAR
"""

import pyupbit
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict
from datetime import datetime


from .models import IchimokuData, PivotPoints
from .momentum import MomentumIndicatorsMixin
from .volume import VolumeIndicatorsMixin
from .trend import TrendIndicatorsMixin


class UpbitAdvancedIndicators(MomentumIndicatorsMixin, VolumeIndicatorsMixin, TrendIndicatorsMixin):
    """Facade composing indicator mixins (SOLID composition, OCP)."""

    def __init__(self, trader=None):
        self.trader = trader

    def get_ohlcv(self, ticker: str, interval: str = "day", count: int = 100) -> pd.DataFrame:
        """OHLCV 데이터 조회"""
        try:
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=count)
            return df
        except Exception as e:
            if self.trader:
                self.trader.log(f"[지표] OHLCV 조회 실패: {e}")
            return pd.DataFrame()

    def get_comprehensive_analysis(self, ticker: str) -> Dict:
        """모든 지표 종합 분석"""
        result = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'indicators': {},
            'signals': {},
            'overall_score': 0,
            'recommendation': 'HOLD'
        }
        
        buy_signals = 0
        sell_signals = 0
        total_signals = 0
        
        # Williams %R
        wr_signal, wr_value = self.check_williams_r_condition(ticker)
        result['indicators']['williams_r'] = wr_value
        result['signals']['williams_r'] = wr_signal
        if wr_signal == 'BUY':
            buy_signals += 1
        elif wr_signal == 'SELL':
            sell_signals += 1
        total_signals += 1
        
        # CCI
        cci_signal, cci_value = self.check_cci_condition(ticker)
        result['indicators']['cci'] = cci_value
        result['signals']['cci'] = cci_signal
        if cci_signal == 'BUY':
            buy_signals += 1
        elif cci_signal == 'SELL':
            sell_signals += 1
        total_signals += 1
        
        # OBV
        obv_signal, obv_ratio = self.calculate_obv_signal(ticker)
        result['indicators']['obv_ratio'] = obv_ratio
        result['signals']['obv'] = obv_signal
        if obv_signal == 'BULLISH':
            buy_signals += 1
        elif obv_signal == 'BEARISH':
            sell_signals += 1
        total_signals += 1
        
        # Ichimoku
        ich_signal, ich_details = self.check_ichimoku_condition(ticker)
        result['indicators']['ichimoku'] = ich_details
        result['signals']['ichimoku'] = ich_signal
        if ich_signal == 'BUY':
            buy_signals += 1
        elif ich_signal == 'SELL':
            sell_signals += 1
        total_signals += 1
        
        # Pivot Points
        pivot_signal, pivot_details = self.check_pivot_condition(ticker)
        result['indicators']['pivot'] = pivot_details
        result['signals']['pivot'] = pivot_signal
        if pivot_signal == 'BUY':
            buy_signals += 1
        elif pivot_signal == 'SELL':
            sell_signals += 1
        total_signals += 1
        
        # Parabolic SAR
        sar_signal, sar_details = self.check_parabolic_sar_condition(ticker)
        result['indicators']['sar'] = sar_details
        result['signals']['sar'] = sar_signal
        if sar_signal == 'BUY':
            buy_signals += 1
        elif sar_signal == 'SELL':
            sell_signals += 1
        total_signals += 1
        
        # 종합 점수 (0~100)
        if total_signals > 0:
            score = ((buy_signals - sell_signals) / total_signals + 1) * 50
            result['overall_score'] = round(score, 1)
        
        # 추천
        if result['overall_score'] >= 70:
            result['recommendation'] = 'STRONG_BUY'
        elif result['overall_score'] >= 55:
            result['recommendation'] = 'BUY'
        elif result['overall_score'] <= 30:
            result['recommendation'] = 'STRONG_SELL'
        elif result['overall_score'] <= 45:
            result['recommendation'] = 'SELL'
        else:
            result['recommendation'] = 'HOLD'
        
        return result
