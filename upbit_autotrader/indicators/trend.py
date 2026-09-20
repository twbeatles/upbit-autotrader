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


from .models import IchimokuData, PivotPoints


class TrendIndicatorsMixin:
    """Trend responsibility: Ichimoku, Pivot, Parabolic SAR (SRP)."""

    get_ohlcv: Any

    def calculate_ichimoku(self, ticker: str) -> Optional[IchimokuData]:
        """일목균형표 계산"""
        df = self.get_ohlcv(ticker, count=80)
        if df.empty or len(df) < 52:
            return None
        
        # 전환선 (9일)
        high_9 = df['high'].rolling(window=9).max()
        low_9 = df['low'].rolling(window=9).min()
        tenkan = (high_9 + low_9) / 2
        
        # 기준선 (26일)
        high_26 = df['high'].rolling(window=26).max()
        low_26 = df['low'].rolling(window=26).min()
        kijun = (high_26 + low_26) / 2
        
        # 선행스팬1 (전환선 + 기준선) / 2, 26일 후행
        senkou_a = (tenkan + kijun) / 2
        
        # 선행스팬2 (52일 고가 + 저가) / 2, 26일 후행
        high_52 = df['high'].rolling(window=52).max()
        low_52 = df['low'].rolling(window=52).min()
        senkou_b = (high_52 + low_52) / 2
        
        # 후행스팬 (현재 종가, 26일 후행 표시)
        chikou = df['close']
        
        return IchimokuData(
            tenkan_sen=float(tenkan.iloc[-1]),
            kijun_sen=float(kijun.iloc[-1]),
            senkou_span_a=float(senkou_a.iloc[-1]),
            senkou_span_b=float(senkou_b.iloc[-1]),
            chikou_span=float(chikou.iloc[-1])
        )

    def check_ichimoku_condition(self, ticker: str) -> Tuple[str, dict]:
        """
        일목균형표 조건 확인
        Returns: (signal, details)
        """
        ichimoku = self.calculate_ichimoku(ticker)
        if not ichimoku:
            return 'NEUTRAL', {}
        
        df = self.get_ohlcv(ticker, count=5)
        if df.empty:
            return 'NEUTRAL', {}
            
        price = df['close'].iloc[-1]
        
        # 구름 위/아래 판단
        cloud_top = max(ichimoku.senkou_span_a, ichimoku.senkou_span_b)
        cloud_bottom = min(ichimoku.senkou_span_a, ichimoku.senkou_span_b)
        
        details = {
            'price': price,
            'tenkan': ichimoku.tenkan_sen,
            'kijun': ichimoku.kijun_sen,
            'cloud_top': cloud_top,
            'cloud_bottom': cloud_bottom
        }
        
        # 매수 신호: 가격이 구름 위, 전환선 > 기준선
        if price > cloud_top and ichimoku.tenkan_sen > ichimoku.kijun_sen:
            return 'BUY', details
        # 매도 신호: 가격이 구름 아래, 전환선 < 기준선
        elif price < cloud_bottom and ichimoku.tenkan_sen < ichimoku.kijun_sen:
            return 'SELL', details
        else:
            return 'NEUTRAL', details

    def calculate_pivot_points(self, ticker: str) -> Optional[PivotPoints]:
        """피봇 포인트 계산"""
        df = self.get_ohlcv(ticker, count=2)
        if df.empty or len(df) < 2:
            return None
            
        # 전일 데이터
        prev = df.iloc[-2]
        h, l, c = prev['high'], prev['low'], prev['close']
        
        pivot = (h + l + c) / 3
        
        return PivotPoints(
            pivot=pivot,
            r1=2 * pivot - l,
            r2=pivot + (h - l),
            r3=h + 2 * (pivot - l),
            s1=2 * pivot - h,
            s2=pivot - (h - l),
            s3=l - 2 * (h - pivot)
        )

    def check_pivot_condition(self, ticker: str) -> Tuple[str, dict]:
        """피봇 포인트 조건 확인"""
        pivots = self.calculate_pivot_points(ticker)
        if not pivots:
            return 'NEUTRAL', {}
            
        df = self.get_ohlcv(ticker, count=2)
        if df.empty:
            return 'NEUTRAL', {}
            
        price = df['close'].iloc[-1]
        
        details = {
            'price': price,
            'pivot': pivots.pivot,
            's1': pivots.s1,
            'r1': pivots.r1
        }
        
        # 지지선 근처: 매수 기회
        if price <= pivots.s1 and price >= pivots.s2:
            return 'BUY', details
        # 저항선 근처: 매도 주의
        elif price >= pivots.r1 and price <= pivots.r2:
            return 'SELL', details
        else:
            return 'NEUTRAL', details

    def calculate_parabolic_sar(self, ticker: str, af_step: float = 0.02, 
                                af_max: float = 0.2) -> Optional[List[float]]:
        """Parabolic SAR 계산"""
        df = self.get_ohlcv(ticker, count=50)
        if df.empty or len(df) < 10:
            return None
            
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        sar = [close[0]]
        ep = high[0]  # Extreme Point
        af = af_step
        trend = 1  # 1: 상승, -1: 하락
        
        for i in range(1, len(df)):
            if trend == 1:  # 상승 추세
                sar_new = sar[-1] + af * (ep - sar[-1])
                sar_new = min(sar_new, low[i-1], low[i] if i > 0 else low[i-1])
                
                if low[i] < sar_new:  # 추세 전환
                    trend = -1
                    sar_new = ep
                    ep = low[i]
                    af = af_step
                else:
                    if high[i] > ep:
                        ep = high[i]
                        af = min(af + af_step, af_max)
            else:  # 하락 추세
                sar_new = sar[-1] + af * (ep - sar[-1])
                sar_new = max(sar_new, high[i-1], high[i] if i > 0 else high[i-1])
                
                if high[i] > sar_new:  # 추세 전환
                    trend = 1
                    sar_new = ep
                    ep = high[i]
                    af = af_step
                else:
                    if low[i] < ep:
                        ep = low[i]
                        af = min(af + af_step, af_max)
            
            sar.append(sar_new)
        
        return sar

    def check_parabolic_sar_condition(self, ticker: str) -> Tuple[str, dict]:
        """Parabolic SAR 조건 확인"""
        sar = self.calculate_parabolic_sar(ticker)
        if not sar or len(sar) < 2:
            return 'NEUTRAL', {}
            
        df = self.get_ohlcv(ticker, count=50)
        if df.empty:
            return 'NEUTRAL', {}
            
        price = df['close'].iloc[-1]
        current_sar = sar[-1]
        prev_sar = sar[-2]
        
        details = {'price': price, 'sar': current_sar, 'prev_sar': prev_sar}
        
        # SAR이 가격 아래: 상승 추세 (매수)
        if current_sar < price:
            return 'BUY', details
        # SAR이 가격 위: 하락 추세 (매도)
        else:
            return 'SELL', details
