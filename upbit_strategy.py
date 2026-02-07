"""
Upbit Pro Algo-Trader - 전략 매니저 모듈
v3.0 (구조 리팩토링 + 고급 기능)

키움증권 자동매매 프로그램의 strategy_manager.py를 참조하여 설계
"""

import datetime
import time
import logging
from typing import Tuple, Optional, Dict, Any, List

try:
    import pyupbit
    import pandas as pd
except ImportError:
    pyupbit = None
    pd = None

from upbit_config import Config


class UpbitStrategyManager:
    """매매 전략 로직 분리 - 키움증권 StrategyManager 참조"""
    
    def __init__(self, trader, config=None):
        """
        Args:
            trader: UpbitProTrader 인스턴스 (UI 및 상태 접근용)
            config: Config 클래스 또는 None
        """
        self.trader = trader
        self.config = config or Config
        self.logger = logging.getLogger('UpbitStrategy')
        
        # =====================================================================
        # v3.0 고급 기능용 상태 변수
        # =====================================================================
        # 연속 손익 추적 (Anti-Martingale)
        self.consecutive_profits = 0
        self.consecutive_losses = 0
        
        # 재진입 쿨다운 추적
        self.cooldown_tickers = {}  # {ticker: cooldown_end_time}
        
        # 보유 시간 추적
        self.holding_start_times = {}  # {ticker: buy_time}
        
        # 최근 가격 추적 (돌파 확인용)
        self.recent_prices = {}  # {ticker: [price1, price2, ...]}
        self.max_recent_prices = 10
        
        # 분할 익절 추적
        self.partial_profit_executed = {}  # {ticker: [executed_levels]}
    
    def log(self, msg: str):
        """로그 출력 (트레이더 로그 연동)"""
        if hasattr(self.trader, 'log'):
            self.trader.log(msg)
        self.logger.info(msg)
    
    # =========================================================================
    # 기술지표 계산 함수들
    # =========================================================================
    def calculate_target_price(self, ticker: str, interval: str) -> Optional[float]:
        """변동성 돌파 목표가 계산"""
        try:
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=2)
            if df is None or len(df) < 2:
                return None
            
            prev_high = df.iloc[-2]['high']
            prev_low = df.iloc[-2]['low']
            volatility = prev_high - prev_low
            
            current_open = df.iloc[-1]['open']
            k = self._get_k_value()
            
            # 갭 분석 적용 (활성화 시)
            if self._is_gap_analysis_enabled():
                k = self.get_gap_adjusted_k(ticker, k)
            
            return current_open + (volatility * k)
        except Exception as e:
            self.logger.error(f"목표가 계산 실패 ({ticker}): {e}")
            return None
    
    def calculate_ma(self, ticker: str, interval: str, period: int = 5) -> Optional[float]:
        """이동평균 계산"""
        try:
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=period + 1)
            if df is None or len(df) < period:
                return None
            return df['close'].rolling(window=period).mean().iloc[-1]
        except Exception as e:
            self.logger.error(f"MA 계산 실패 ({ticker}): {e}")
            return None
    
    def calculate_rsi(self, ticker: str, period: int = 14) -> float:
        """RSI 계산"""
        try:
            interval = self._get_candle_interval()
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=period + 2)
            if df is None or len(df) < period + 1:
                return 50
            
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = (-delta).where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=period).mean().iloc[-1]
            avg_loss = loss.rolling(window=period).mean().iloc[-1]
            
            if avg_loss == 0:
                return 100
            
            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))
        except Exception as e:
            self.logger.error(f"RSI 계산 실패 ({ticker}): {e}")
            return 50
    
    def calculate_macd(self, ticker: str) -> Tuple[float, float, float]:
        """MACD 계산 (MACD, Signal, Histogram 반환)"""
        try:
            interval = self._get_candle_interval()
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=50)
            if df is None or len(df) < 30:
                return 0, 0, 0
            
            close = df['close']
            
            ema_fast = close.ewm(span=Config.DEFAULT_MACD_FAST, adjust=False).mean()
            ema_slow = close.ewm(span=Config.DEFAULT_MACD_SLOW, adjust=False).mean()
            
            macd = ema_fast - ema_slow
            signal = macd.ewm(span=Config.DEFAULT_MACD_SIGNAL, adjust=False).mean()
            histogram = macd - signal
            
            return macd.iloc[-1], signal.iloc[-1], histogram.iloc[-1]
        except Exception as e:
            self.logger.error(f"MACD 계산 실패 ({ticker}): {e}")
            return 0, 0, 0
    
    def calculate_bollinger_bands(self, ticker: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """볼린저 밴드 계산 (상단, 중간, 하단 반환)"""
        try:
            interval = self._get_candle_interval()
            period = Config.DEFAULT_BB_PERIOD
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=period + 5)
            if df is None or len(df) < period:
                return None, None, None
            
            close = df['close']
            middle = close.rolling(window=period).mean().iloc[-1]
            std = close.rolling(window=period).std().iloc[-1]
            
            upper = middle + (std * Config.DEFAULT_BB_STD)
            lower = middle - (std * Config.DEFAULT_BB_STD)
            
            return upper, middle, lower
        except Exception as e:
            self.logger.error(f"볼린저 밴드 계산 실패 ({ticker}): {e}")
            return None, None, None
    
    def calculate_atr(self, ticker: str, period: int = 14) -> Optional[float]:
        """ATR (Average True Range) 계산"""
        try:
            interval = self._get_candle_interval()
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=period + 5)
            if df is None or len(df) < period:
                return None
            
            high = df['high']
            low = df['low']
            close = df['close']
            
            tr1 = high - low
            tr2 = (high - close.shift()).abs()
            tr3 = (low - close.shift()).abs()
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean().iloc[-1]
            return atr
        except Exception as e:
            self.logger.error(f"ATR 계산 실패 ({ticker}): {e}")
            return None
    
    def calculate_volume_avg(self, ticker: str, period: int = 20) -> Tuple[Optional[float], Optional[float]]:
        """평균 거래량 계산"""
        try:
            interval = self._get_candle_interval()
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=period + 1)
            if df is None or len(df) < period:
                return None, None
            
            current_volume = df.iloc[-1]['volume']
            avg_volume = df['volume'].iloc[:-1].mean()
            
            return current_volume, avg_volume
        except Exception as e:
            return None, None
    
    def calculate_stoch_rsi(self, ticker: str, rsi_period: int = 14, stoch_period: int = 14,
                            k_period: int = 3, d_period: int = 3) -> Tuple[float, float]:
        """스토캐스틱 RSI 계산"""
        try:
            interval = self._get_candle_interval()
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=rsi_period + stoch_period + 10)
            if df is None or len(df) < rsi_period + stoch_period:
                return 50, 50
            
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = (-delta).where(delta < 0, 0)
            avg_gain = gain.rolling(window=rsi_period).mean()
            avg_loss = loss.rolling(window=rsi_period).mean()
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            rsi_min = rsi.rolling(window=stoch_period).min()
            rsi_max = rsi.rolling(window=stoch_period).max()
            stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min) * 100
            
            k = stoch_rsi.rolling(window=k_period).mean().iloc[-1]
            d = stoch_rsi.rolling(window=d_period).mean().iloc[-1]
            
            return k if not pd.isna(k) else 50, d if not pd.isna(d) else 50
        except Exception as e:
            self.logger.error(f"스토캐스틱 RSI 계산 실패 ({ticker}): {e}")
            return 50, 50
    
    def calculate_dmi_adx(self, ticker: str, period: int = 14) -> Tuple[float, float, float]:
        """DMI와 ADX 계산 - 추세 강도 측정"""
        try:
            interval = self._get_candle_interval()
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=period * 3)
            if df is None or len(df) < period * 2:
                return 0, 0, 0
            
            high = df['high']
            low = df['low']
            close = df['close']
            
            plus_dm = high.diff()
            minus_dm = -low.diff()
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm < 0] = 0
            
            plus_dm[(plus_dm < minus_dm) | (plus_dm < 0)] = 0
            minus_dm[(minus_dm < plus_dm) | (minus_dm < 0)] = 0
            
            tr1 = high - low
            tr2 = (high - close.shift()).abs()
            tr3 = (low - close.shift()).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            atr = tr.rolling(window=period).mean()
            atr_safe = atr.replace(0, float('nan'))
            plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr_safe)
            minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr_safe)
            
            di_sum = plus_di + minus_di
            di_sum_safe = di_sum.replace(0, float('nan'))
            dx = 100 * (abs(plus_di - minus_di) / di_sum_safe)
            adx = dx.rolling(window=period).mean()
            
            plus_di_val = plus_di.iloc[-1]
            minus_di_val = minus_di.iloc[-1]
            adx_val = adx.iloc[-1]
            
            return (
                0 if pd.isna(plus_di_val) else plus_di_val,
                0 if pd.isna(minus_di_val) else minus_di_val,
                0 if pd.isna(adx_val) else adx_val
            )
        except Exception as e:
            self.logger.error(f"DMI/ADX 계산 실패 ({ticker}): {e}")
            return 0, 0, 0
    
    def calculate_entry_score(self, ticker: str, curr_price: float, info: Dict) -> Tuple[int, List[str]]:
        """진입 점수 계산 (0~100점)"""
        score = 0
        reasons = []
        weights = Config.ENTRY_WEIGHTS
        
        # 1. 목표가 돌파
        if curr_price >= info.get('target', 0):
            score += weights['target_break']
            reasons.append(f"+{weights['target_break']} 목표가 돌파")
        
        # 2. MA5 필터
        if curr_price >= info.get('ma5', 0):
            score += weights['ma_filter']
            reasons.append(f"+{weights['ma_filter']} MA5 위")
        
        # 3. RSI 최적 구간
        rsi = self.calculate_rsi(ticker, self._get_rsi_period())
        if 30 <= rsi <= 70:
            score += weights['rsi_optimal']
            reasons.append(f"+{weights['rsi_optimal']} RSI {rsi:.1f} (최적)")
        elif rsi < 30:
            score += weights['rsi_optimal'] // 2
            reasons.append(f"+{weights['rsi_optimal']//2} RSI {rsi:.1f} (과매도)")
        
        # 4. MACD 골든크로스
        macd, signal, histogram = self.calculate_macd(ticker)
        if macd > signal:
            score += weights['macd_golden']
            reasons.append(f"+{weights['macd_golden']} MACD 골든크로스")
        
        # 5. 거래량 확인
        curr_vol, avg_vol = self.calculate_volume_avg(ticker, Config.DEFAULT_VOLUME_PERIOD)
        if curr_vol and avg_vol:
            required_vol = avg_vol * self._get_volume_multiplier()
            if curr_vol >= required_vol:
                score += weights['volume_confirm']
                reasons.append(f"+{weights['volume_confirm']} 거래량 충분")
        
        # 6. 볼린저 밴드 포지션
        upper, middle, lower = self.calculate_bollinger_bands(ticker)
        if lower and middle:
            if lower <= curr_price <= middle:
                score += weights['bb_position']
                reasons.append(f"+{weights['bb_position']} BB 최적 구간")
            elif middle < curr_price <= upper:
                score += weights['bb_position'] // 2
                reasons.append(f"+{weights['bb_position']//2} BB 중상단")
        
        return score, reasons
    
    # =========================================================================
    # v3.0 고급 기능: 재진입 쿨다운
    # =========================================================================
    def set_cooldown(self, ticker: str, minutes: int = None):
        """매도 후 재진입 쿨다운 설정"""
        minutes = minutes or Config.DEFAULT_COOLDOWN_MINUTES
        self.cooldown_tickers[ticker] = datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        self.log(f"[{ticker}] 재진입 쿨다운 설정: {minutes}분")
    
    def check_cooldown(self, ticker: str) -> bool:
        """쿨다운 상태 확인 (True = 매수 가능)"""
        if not self._is_cooldown_enabled():
            return True
        
        if ticker not in self.cooldown_tickers:
            return True
        
        if datetime.datetime.now() > self.cooldown_tickers[ticker]:
            del self.cooldown_tickers[ticker]
            return True
        
        remaining = (self.cooldown_tickers[ticker] - datetime.datetime.now()).seconds // 60
        self.log(f"[{ticker}] 재진입 쿨다운 중 (남은 시간: {remaining}분)")
        return False
    
    def clear_cooldown(self, ticker: str):
        """쿨다운 해제"""
        if ticker in self.cooldown_tickers:
            del self.cooldown_tickers[ticker]
    
    # =========================================================================
    # v3.0 고급 기능: 시간 기반 청산
    # =========================================================================
    def set_holding_start(self, ticker: str):
        """보유 시작 시간 기록"""
        self.holding_start_times[ticker] = datetime.datetime.now()
    
    def check_holding_time_exit(self, ticker: str, max_hours: int = None) -> bool:
        """보유 시간 초과 시 청산 필요 여부"""
        if not self._is_time_exit_enabled():
            return False
        
        max_hours = max_hours or Config.DEFAULT_MAX_HOLDING_HOURS
        
        if ticker not in self.holding_start_times:
            return False
        
        buy_time = self.holding_start_times[ticker]
        elapsed = datetime.datetime.now() - buy_time
        hours_held = elapsed.total_seconds() / 3600
        
        if hours_held > max_hours:
            self.log(f"[{ticker}] 보유 시간 초과 ({hours_held:.1f}h > {max_hours}h) → 시간 청산")
            return True
        return False
    
    def clear_holding_start(self, ticker: str):
        """보유 시간 기록 삭제"""
        if ticker in self.holding_start_times:
            del self.holding_start_times[ticker]
    
    # =========================================================================
    # v3.0 고급 기능: 동적 포지션 사이징 (Anti-Martingale)
    # =========================================================================
    def calculate_dynamic_position_size(self, ticker: str) -> float:
        """연속 손익에 따른 포지션 크기 조정"""
        if not self._is_dynamic_position_enabled():
            return self._get_betting_ratio()
        
        base_ratio = self._get_betting_ratio()
        
        if self.consecutive_losses >= Config.DYNAMIC_POSITION_LOSS_THRESHOLD:
            # 연속 손실 → 투자 비율 축소
            adjusted = base_ratio * Config.DYNAMIC_POSITION_LOSS_RATIO
            self.log(f"[동적 포지션] 연속 {self.consecutive_losses}회 손실 → {adjusted:.1f}% 투자")
            return adjusted
        elif self.consecutive_profits >= Config.DYNAMIC_POSITION_WIN_THRESHOLD:
            # 연속 이익 → 투자 비율 확대
            adjusted = min(base_ratio * Config.DYNAMIC_POSITION_WIN_RATIO, 
                          Config.DYNAMIC_POSITION_MAX_RATIO)
            self.log(f"[동적 포지션] 연속 {self.consecutive_profits}회 이익 → {adjusted:.1f}% 투자")
            return adjusted
        
        return base_ratio
    
    def update_consecutive_results(self, is_profit: bool):
        """연속 손익 결과 업데이트"""
        if is_profit:
            self.consecutive_profits += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
            self.consecutive_profits = 0
    
    def reset_consecutive_results(self):
        """연속 손익 초기화"""
        self.consecutive_profits = 0
        self.consecutive_losses = 0
    
    # =========================================================================
    # v3.0 고급 기능: MTF (다중 시간프레임) 분석
    # =========================================================================
    def check_mtf_condition(self, ticker: str) -> bool:
        """일봉과 단기봉의 추세가 일치할 때만 매수"""
        if not self._is_mtf_enabled():
            return True  # 비활성화 시 통과
        
        try:
            # 장기 (일봉) 추세 확인
            long_trend = self._get_trend(ticker, Config.MTF_LONG_INTERVAL)
            # 단기 추세 확인
            short_trend = self._get_trend(ticker, Config.MTF_SHORT_INTERVAL)
            
            result = long_trend == short_trend == 'UP'
            if not result:
                self.log(f"[{ticker}] MTF 불일치 (장기: {long_trend}, 단기: {short_trend}) → 진입 보류")
            return result
        except Exception as e:
            self.logger.error(f"MTF 분석 실패 ({ticker}): {e}")
            return True  # 오류 시 통과
    
    def _get_trend(self, ticker: str, interval: str, period: int = 5) -> str:
        """추세 판단 (UP/DOWN/SIDEWAYS)"""
        try:
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=period + 1)
            if df is None or len(df) < period:
                return 'SIDEWAYS'
            
            ma = df['close'].rolling(window=period).mean()
            current = df['close'].iloc[-1]
            ma_current = ma.iloc[-1]
            ma_prev = ma.iloc[-2]
            
            if current > ma_current and ma_current > ma_prev:
                return 'UP'
            elif current < ma_current and ma_current < ma_prev:
                return 'DOWN'
            else:
                return 'SIDEWAYS'
        except:
            return 'SIDEWAYS'
    
    # =========================================================================
    # v3.0 고급 기능: 갭 분석
    # =========================================================================
    def analyze_gap(self, ticker: str) -> Tuple[str, float]:
        """시가갭 분석
        
        Returns:
            (갭 유형, 갭 비율%)
            갭 유형: 'gap_up', 'gap_down', 'no_gap'
        """
        try:
            interval = self._get_candle_interval()
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=2)
            if df is None or len(df) < 2:
                return 'no_gap', 0.0
            
            prev_close = df.iloc[-2]['close']
            curr_open = df.iloc[-1]['open']
            
            gap_ratio = (curr_open - prev_close) / prev_close * 100
            
            if gap_ratio > Config.GAP_THRESHOLD:
                return 'gap_up', gap_ratio
            elif gap_ratio < -Config.GAP_THRESHOLD:
                return 'gap_down', gap_ratio
            else:
                return 'no_gap', gap_ratio
        except Exception as e:
            self.logger.error(f"갭 분석 실패 ({ticker}): {e}")
            return 'no_gap', 0.0
    
    def get_gap_adjusted_k(self, ticker: str, base_k: float) -> float:
        """갭에 따른 K값 조정"""
        gap_type, gap_ratio = self.analyze_gap(ticker)
        
        if gap_type == 'gap_up':
            adjusted_k = base_k * Config.GAP_UP_K_ADJUST
            self.log(f"[{ticker}] 갭업 {gap_ratio:.1f}% → K값 {base_k:.2f} → {adjusted_k:.2f}")
            return adjusted_k
        elif gap_type == 'gap_down':
            adjusted_k = base_k * Config.GAP_DOWN_K_ADJUST
            self.log(f"[{ticker}] 갭다운 {gap_ratio:.1f}% → K값 {base_k:.2f} → {adjusted_k:.2f}")
            return adjusted_k
        
        return base_k
    
    # =========================================================================
    # v3.0 고급 기능: 돌파 확인 (N틱 유지)
    # =========================================================================
    def update_recent_price(self, ticker: str, price: float):
        """최근 가격 업데이트"""
        if ticker not in self.recent_prices:
            self.recent_prices[ticker] = []
        
        self.recent_prices[ticker].append(price)
        
        # 최대 개수 제한
        if len(self.recent_prices[ticker]) > self.max_recent_prices:
            self.recent_prices[ticker] = self.recent_prices[ticker][-self.max_recent_prices:]
    
    def check_breakout_confirmation(self, ticker: str, target_price: float, 
                                     confirm_ticks: int = None) -> bool:
        """목표가 돌파 후 N틱 유지 확인"""
        if not self._is_breakout_confirm_enabled():
            return True  # 비활성화 시 통과
        
        confirm_ticks = confirm_ticks or Config.DEFAULT_BREAKOUT_CONFIRM_TICKS
        
        if ticker not in self.recent_prices:
            return False
        
        prices = self.recent_prices[ticker]
        if len(prices) < confirm_ticks:
            return False
        
        # 최근 N개 가격이 모두 목표가 이상인지 확인
        result = all(p >= target_price for p in prices[-confirm_ticks:])
        if not result:
            self.log(f"[{ticker}] 돌파 확인 대기 ({confirm_ticks}틱 미충족)")
        return result
    
    def clear_recent_prices(self, ticker: str):
        """최근 가격 기록 삭제"""
        if ticker in self.recent_prices:
            del self.recent_prices[ticker]
    
    # =========================================================================
    # v3.0 고급 기능: 분할 익절 추적
    # =========================================================================
    def check_partial_take_profit(self, ticker: str, profit_rate: float) -> Optional[Dict]:
        """단계별 익절 조건 확인
        
        Returns:
            {'sell_ratio': 매도비율, 'level': 단계, 'rate': 수익률} 또는 None
        """
        if ticker not in self.partial_profit_executed:
            self.partial_profit_executed[ticker] = []
        
        executed = self.partial_profit_executed[ticker]
        
        for level in Config.PARTIAL_TAKE_PROFIT:
            rate = level['rate']
            sell_ratio = level['sell_ratio']
            
            if rate in executed:
                continue
            
            if profit_rate >= rate:
                return {'sell_ratio': sell_ratio, 'level': rate, 'rate': rate}
        
        return None
    
    def mark_partial_profit_executed(self, ticker: str, level: float):
        """분할 익절 실행 표시"""
        if ticker not in self.partial_profit_executed:
            self.partial_profit_executed[ticker] = []
        
        if level not in self.partial_profit_executed[ticker]:
            self.partial_profit_executed[ticker].append(level)
    
    def clear_partial_profit(self, ticker: str):
        """분할 익절 기록 삭제"""
        if ticker in self.partial_profit_executed:
            del self.partial_profit_executed[ticker]
    
    # =========================================================================
    # 헬퍼 메서드들 (트레이더 UI 접근)
    # =========================================================================
    def _get_candle_interval(self) -> str:
        """현재 설정된 캔들 간격 조회"""
        if hasattr(self.trader, 'combo_candle'):
            return Config.CANDLE_INTERVALS.get(
                self.trader.combo_candle.currentText(), 
                'minute240'
            )
        return 'minute240'
    
    def _get_k_value(self) -> float:
        """K값 조회"""
        if hasattr(self.trader, 'spin_k'):
            return self.trader.spin_k.value()
        return Config.DEFAULT_K_VALUE
    
    def _get_betting_ratio(self) -> float:
        """베팅 비율 조회"""
        if hasattr(self.trader, 'spin_betting'):
            return self.trader.spin_betting.value()
        return Config.DEFAULT_BETTING_RATIO
    
    def _get_rsi_period(self) -> int:
        """RSI 기간 조회"""
        if hasattr(self.trader, 'spin_rsi_period'):
            return self.trader.spin_rsi_period.value()
        return Config.DEFAULT_RSI_PERIOD
    
    def _get_volume_multiplier(self) -> float:
        """거래량 배수 조회"""
        if hasattr(self.trader, 'spin_volume_mult'):
            return self.trader.spin_volume_mult.value()
        return Config.DEFAULT_VOLUME_MULTIPLIER
    
    def _is_cooldown_enabled(self) -> bool:
        """쿨다운 활성화 여부"""
        if hasattr(self.trader, 'chk_use_cooldown'):
            return self.trader.chk_use_cooldown.isChecked()
        return Config.DEFAULT_USE_COOLDOWN
    
    def _is_time_exit_enabled(self) -> bool:
        """시간 청산 활성화 여부"""
        if hasattr(self.trader, 'chk_use_time_exit'):
            return self.trader.chk_use_time_exit.isChecked()
        return Config.DEFAULT_USE_TIME_EXIT
    
    def _is_dynamic_position_enabled(self) -> bool:
        """동적 포지션 활성화 여부"""
        if hasattr(self.trader, 'chk_use_dynamic_position'):
            return self.trader.chk_use_dynamic_position.isChecked()
        return Config.DEFAULT_USE_DYNAMIC_POSITION
    
    def _is_mtf_enabled(self) -> bool:
        """MTF 활성화 여부"""
        if hasattr(self.trader, 'chk_use_mtf'):
            return self.trader.chk_use_mtf.isChecked()
        return Config.DEFAULT_USE_MTF
    
    def _is_gap_analysis_enabled(self) -> bool:
        """갭 분석 활성화 여부"""
        if hasattr(self.trader, 'chk_use_gap'):
            return self.trader.chk_use_gap.isChecked()
        return Config.DEFAULT_USE_GAP_ANALYSIS
    
    def _is_breakout_confirm_enabled(self) -> bool:
        """돌파 확인 활성화 여부"""
        if hasattr(self.trader, 'chk_use_breakout_confirm'):
            return self.trader.chk_use_breakout_confirm.isChecked()
        return Config.DEFAULT_USE_BREAKOUT_CONFIRM
