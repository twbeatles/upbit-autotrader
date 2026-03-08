from __future__ import annotations

# Runtime bindings injected by legacy_strategy facade
Config = None
pd = None
pyupbit = None
datetime = None
time = None


def bind_runtime(**kwargs):
    globals().update(kwargs)



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
