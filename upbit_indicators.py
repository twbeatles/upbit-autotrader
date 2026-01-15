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


@dataclass
class IchimokuData:
    """일목균형표 데이터"""
    tenkan_sen: float       # 전환선 (9)
    kijun_sen: float        # 기준선 (26)
    senkou_span_a: float    # 선행스팬1
    senkou_span_b: float    # 선행스팬2 (52)
    chikou_span: float      # 후행스팬


@dataclass
class PivotPoints:
    """피봇 포인트 데이터"""
    pivot: float            # 피봇
    r1: float               # 저항선1
    r2: float               # 저항선2
    r3: float               # 저항선3
    s1: float               # 지지선1
    s2: float               # 지지선2
    s3: float               # 지지선3


class UpbitAdvancedIndicators:
    """Upbit 고급 기술지표 계산 클래스"""
    
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
    
    # =========================================================================
    # Williams %R
    # =========================================================================
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
        return float(wr.iloc[-1])
    
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
    
    # =========================================================================
    # CCI (Commodity Channel Index)
    # =========================================================================
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
    
    # =========================================================================
    # OBV (On-Balance Volume)
    # =========================================================================
    def calculate_obv(self, ticker: str, count: int = 50) -> Optional[List[float]]:
        """OBV 계산"""
        df = self.get_ohlcv(ticker, count=count)
        if df.empty or len(df) < 2:
            return None
            
        obv = [0]
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.append(obv[-1] + df['volume'].iloc[i])
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.append(obv[-1] - df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
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
        
        current = obv[-1]
        ma = obv_ma.iloc[-1]
        
        if ma == 0:
            return 'NEUTRAL', 0.0
            
        ratio = (current - ma) / abs(ma) * 100
        
        if ratio > 5:
            return 'BULLISH', ratio
        elif ratio < -5:
            return 'BEARISH', ratio
        else:
            return 'NEUTRAL', ratio
    
    # =========================================================================
    # Ichimoku Cloud (일목균형표)
    # =========================================================================
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
    
    # =========================================================================
    # Pivot Points
    # =========================================================================
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
    
    # =========================================================================
    # Parabolic SAR
    # =========================================================================
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
    
    # =========================================================================
    # 종합 분석
    # =========================================================================
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
