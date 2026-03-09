from __future__ import annotations

from typing import Any, Dict, Optional, cast

# Runtime bindings injected by legacy_strategy facade
Config = cast(Any, None)
pd = cast(Any, None)
pyupbit = cast(Any, None)
datetime = cast(Any, None)
time = cast(Any, None)


def bind_runtime(**kwargs):
    globals().update(kwargs)



def set_cooldown(self, ticker: str, minutes: int | None = None):
    """매도 후 재진입 쿨다운 설정"""
    minutes = int(minutes or Config.DEFAULT_COOLDOWN_MINUTES)
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


def set_holding_start(self, ticker: str):
    """보유 시작 시간 기록"""
    self.holding_start_times[ticker] = datetime.datetime.now()


def check_holding_time_exit(self, ticker: str, max_hours: int | None = None) -> bool:
    """보유 시간 초과 시 청산 필요 여부"""
    if not self._is_time_exit_enabled():
        return False
    
    max_hours = int(max_hours or Config.DEFAULT_MAX_HOLDING_HOURS)
    
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
