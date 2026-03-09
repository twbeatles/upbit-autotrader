from __future__ import annotations

from typing import Any, Tuple, cast

# Runtime bindings injected by legacy_strategy facade
Config = cast(Any, None)
pd = cast(Any, None)
pyupbit = cast(Any, None)
datetime = cast(Any, None)
time = cast(Any, None)


def bind_runtime(**kwargs):
    globals().update(kwargs)



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
        return True


def _get_trend(self, ticker: str, interval: str, period: int = 5) -> str:
    """추세 판단 (UP/DOWN/SIDEWAYS)"""
    try:
        cache_key = (ticker, interval, period)
        now_ts = time.time()
        ttl = self._get_interval_cache_ttl(interval)
        cached = self._trend_cache.get(cache_key)
        if cached and (now_ts - cached.get("ts", 0)) < ttl:
            return cached.get("trend", "SIDEWAYS")

        df = pyupbit.get_ohlcv(ticker, interval=interval, count=period + 1)
        if df is None or len(df) < period:
            return 'SIDEWAYS'
        
        ma = df['close'].rolling(window=period).mean()
        current = df['close'].iloc[-1]
        ma_current = ma.iloc[-1]
        ma_prev = ma.iloc[-2]
        
        if current > ma_current and ma_current > ma_prev:
            trend = 'UP'
        elif current < ma_current and ma_current < ma_prev:
            trend = 'DOWN'
        else:
            trend = 'SIDEWAYS'
        self._trend_cache[cache_key] = {"ts": now_ts, "trend": trend}
        return trend
    except:
        return 'SIDEWAYS'


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


def update_recent_price(self, ticker: str, price: float):
    """최근 가격 업데이트"""
    if ticker not in self.recent_prices:
        self.recent_prices[ticker] = []
    
    self.recent_prices[ticker].append(price)
    
    # 최대 개수 제한
    if len(self.recent_prices[ticker]) > self.max_recent_prices:
        self.recent_prices[ticker] = self.recent_prices[ticker][-self.max_recent_prices:]


def check_breakout_confirmation(self, ticker: str, target_price: float, 
                                 confirm_ticks: int | None = None) -> bool:
    """목표가 돌파 후 N틱 유지 확인"""
    if not self._is_breakout_confirm_enabled():
        return True  # 비활성화 시 통과
    
    confirm_ticks = int(confirm_ticks or Config.DEFAULT_BREAKOUT_CONFIRM_TICKS)
    
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
