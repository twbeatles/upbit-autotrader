"""
전략 모듈
Upbit Pro Algo-Trader v3.0

다양한 트레이딩 전략 클래스 정의
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from enum import Enum


class SignalType(Enum):
    """시그널 유형"""
    NONE = 0
    BUY = 1
    SELL = 2


@dataclass
class Signal:
    """트레이딩 시그널"""
    signal_type: SignalType
    price: float = 0
    reason: str = ""
    score: float = 0  # 0~100


class BaseStrategy(ABC):
    """기본 전략 추상 클래스"""
    
    name: str = "BaseStrategy"
    description: str = ""
    
    @abstractmethod
    def check_buy_signal(self, data: dict) -> Signal:
        """매수 시그널 확인"""
        pass
    
    @abstractmethod
    def check_sell_signal(self, data: dict) -> Signal:
        """매도 시그널 확인"""
        pass
    
    @abstractmethod
    def get_params(self) -> dict:
        """현재 파라미터 반환"""
        pass
    
    @abstractmethod
    def set_params(self, params: dict):
        """파라미터 설정"""
        pass


class VolatilityBreakout(BaseStrategy):
    """변동성 돌파 전략 (래리 윌리엄스)"""
    
    name = "변동성 돌파"
    description = "전일 변동폭을 이용한 목표가 돌파 전략"
    
    def __init__(self):
        self.k_value = 0.4
        self.use_ma_filter = True
        self.use_rsi_filter = True
        self.rsi_upper = 70
        self.ts_start = 5.0
        self.ts_stop = 2.0
        self.loss_cut = 3.0
    
    def check_buy_signal(self, data: dict) -> Signal:
        """매수 시그널 확인"""
        current_price = data.get('current_price', 0)
        target_price = data.get('target_price', 0)
        ma5 = data.get('ma5', 0)
        rsi = data.get('rsi', 50)
        
        # 기본 조건: 목표가 돌파
        if current_price < target_price:
            return Signal(SignalType.NONE)
        
        # MA5 필터
        if self.use_ma_filter and current_price < ma5:
            return Signal(SignalType.NONE, reason="MA5 하회")
        
        # RSI 필터
        if self.use_rsi_filter and rsi >= self.rsi_upper:
            return Signal(SignalType.NONE, reason=f"RSI 과매수 ({rsi:.1f})")
        
        score = 100
        reason = f"목표가 돌파 (K={self.k_value})"
        
        return Signal(SignalType.BUY, price=current_price, reason=reason, score=score)
    
    def check_sell_signal(self, data: dict) -> Signal:
        """매도 시그널 확인"""
        current_price = data.get('current_price', 0)
        buy_price = data.get('buy_price', 0)
        high_since_buy = data.get('high_since_buy', 0)
        
        if buy_price == 0:
            return Signal(SignalType.NONE)
        
        profit_rate = (current_price - buy_price) / buy_price * 100
        max_profit_rate = (high_since_buy - buy_price) / buy_price * 100 if high_since_buy > 0 else 0
        
        # 손절
        if profit_rate <= -self.loss_cut:
            return Signal(
                SignalType.SELL, 
                price=current_price, 
                reason=f"손절 ({profit_rate:.2f}%)"
            )
        
        # 트레일링 스톱
        if max_profit_rate >= self.ts_start:
            drop = (high_since_buy - current_price) / high_since_buy * 100
            if drop >= self.ts_stop:
                return Signal(
                    SignalType.SELL,
                    price=current_price,
                    reason=f"트레일링 스톱 (고점 대비 -{drop:.2f}%)"
                )
        
        return Signal(SignalType.NONE)
    
    def get_params(self) -> dict:
        return {
            'k_value': self.k_value,
            'use_ma_filter': self.use_ma_filter,
            'use_rsi_filter': self.use_rsi_filter,
            'rsi_upper': self.rsi_upper,
            'ts_start': self.ts_start,
            'ts_stop': self.ts_stop,
            'loss_cut': self.loss_cut
        }
    
    def set_params(self, params: dict):
        self.k_value = params.get('k_value', self.k_value)
        self.use_ma_filter = params.get('use_ma_filter', self.use_ma_filter)
        self.use_rsi_filter = params.get('use_rsi_filter', self.use_rsi_filter)
        self.rsi_upper = params.get('rsi_upper', self.rsi_upper)
        self.ts_start = params.get('ts_start', self.ts_start)
        self.ts_stop = params.get('ts_stop', self.ts_stop)
        self.loss_cut = params.get('loss_cut', self.loss_cut)


class GoldenCross(BaseStrategy):
    """골든크로스 전략 (이동평균 교차)"""
    
    name = "골든크로스"
    description = "단기 이동평균이 장기 이동평균을 상향 돌파할 때 매수"
    
    def __init__(self):
        self.short_period = 5
        self.long_period = 20
        self.ts_start = 5.0
        self.ts_stop = 2.0
        self.loss_cut = 3.0
    
    def check_buy_signal(self, data: dict) -> Signal:
        """매수 시그널: 골든크로스 발생"""
        ma_short = data.get('ma_short', 0)
        ma_long = data.get('ma_long', 0)
        prev_ma_short = data.get('prev_ma_short', 0)
        prev_ma_long = data.get('prev_ma_long', 0)
        current_price = data.get('current_price', 0)
        
        # 골든크로스: 이전에 단기 < 장기, 현재 단기 > 장기
        if prev_ma_short < prev_ma_long and ma_short > ma_long:
            return Signal(
                SignalType.BUY,
                price=current_price,
                reason=f"골든크로스 (MA{self.short_period} > MA{self.long_period})",
                score=80
            )
        
        return Signal(SignalType.NONE)
    
    def check_sell_signal(self, data: dict) -> Signal:
        """매도 시그널: 데드크로스 또는 손절/익절"""
        ma_short = data.get('ma_short', 0)
        ma_long = data.get('ma_long', 0)
        prev_ma_short = data.get('prev_ma_short', 0)
        prev_ma_long = data.get('prev_ma_long', 0)
        current_price = data.get('current_price', 0)
        buy_price = data.get('buy_price', 0)
        high_since_buy = data.get('high_since_buy', 0)
        
        if buy_price == 0:
            return Signal(SignalType.NONE)
        
        profit_rate = (current_price - buy_price) / buy_price * 100
        max_profit_rate = (high_since_buy - buy_price) / buy_price * 100 if high_since_buy > 0 else 0
        
        # 손절
        if profit_rate <= -self.loss_cut:
            return Signal(
                SignalType.SELL,
                price=current_price,
                reason=f"손절 ({profit_rate:.2f}%)"
            )
        
        # 데드크로스
        if prev_ma_short > prev_ma_long and ma_short < ma_long:
            return Signal(
                SignalType.SELL,
                price=current_price,
                reason="데드크로스"
            )
        
        # 트레일링 스톱
        if max_profit_rate >= self.ts_start:
            drop = (high_since_buy - current_price) / high_since_buy * 100
            if drop >= self.ts_stop:
                return Signal(
                    SignalType.SELL,
                    price=current_price,
                    reason=f"트레일링 스톱 (고점 대비 -{drop:.2f}%)"
                )
        
        return Signal(SignalType.NONE)
    
    def get_params(self) -> dict:
        return {
            'short_period': self.short_period,
            'long_period': self.long_period,
            'ts_start': self.ts_start,
            'ts_stop': self.ts_stop,
            'loss_cut': self.loss_cut
        }
    
    def set_params(self, params: dict):
        self.short_period = params.get('short_period', self.short_period)
        self.long_period = params.get('long_period', self.long_period)
        self.ts_start = params.get('ts_start', self.ts_start)
        self.ts_stop = params.get('ts_stop', self.ts_stop)
        self.loss_cut = params.get('loss_cut', self.loss_cut)


class GridTrading(BaseStrategy):
    """그리드 매매 전략"""
    
    name = "그리드 매매"
    description = "일정 가격 간격으로 분할 매수/매도하여 수익 실현"
    
    def __init__(self):
        self.grid_count = 5          # 그리드 개수
        self.grid_spacing = 2.0      # 그리드 간격 (%)
        self.grids: Dict[float, bool] = {}  # 가격대별 매수 여부
        self.base_price = 0          # 기준가
        self.take_profit = 1.0       # 개별 익절 비율 (%)
    
    def setup_grids(self, base_price: float):
        """그리드 설정"""
        self.base_price = base_price
        self.grids = {}
        
        for i in range(self.grid_count):
            # 기준가 아래로 그리드 생성
            grid_price = base_price * (1 - (self.grid_spacing / 100) * (i + 1))
            self.grids[grid_price] = False  # False = 아직 매수 안함
    
    def check_buy_signal(self, data: dict) -> Signal:
        """매수 시그널: 그리드 가격 도달"""
        current_price = data.get('current_price', 0)
        
        for grid_price, bought in self.grids.items():
            if not bought and current_price <= grid_price:
                self.grids[grid_price] = True
                return Signal(
                    SignalType.BUY,
                    price=current_price,
                    reason=f"그리드 매수 ({grid_price:,.0f})",
                    score=70
                )
        
        return Signal(SignalType.NONE)
    
    def check_sell_signal(self, data: dict) -> Signal:
        """매도 시그널: 개별 그리드 익절"""
        current_price = data.get('current_price', 0)
        positions = data.get('positions', [])  # [(buy_price, qty), ...]
        
        for buy_price, qty in positions:
            profit_rate = (current_price - buy_price) / buy_price * 100
            if profit_rate >= self.take_profit:
                return Signal(
                    SignalType.SELL,
                    price=current_price,
                    reason=f"그리드 익절 (+{profit_rate:.2f}%)"
                )
        
        return Signal(SignalType.NONE)
    
    def get_params(self) -> dict:
        return {
            'grid_count': self.grid_count,
            'grid_spacing': self.grid_spacing,
            'take_profit': self.take_profit
        }
    
    def set_params(self, params: dict):
        self.grid_count = params.get('grid_count', self.grid_count)
        self.grid_spacing = params.get('grid_spacing', self.grid_spacing)
        self.take_profit = params.get('take_profit', self.take_profit)


class RSIStrategy(BaseStrategy):
    """RSI 역추세 전략"""
    
    name = "RSI 역추세"
    description = "RSI 과매도시 매수, 과매수시 매도"
    
    def __init__(self):
        self.rsi_period = 14
        self.oversold = 30      # 과매도 기준
        self.overbought = 70    # 과매수 기준
        self.loss_cut = 3.0
    
    def check_buy_signal(self, data: dict) -> Signal:
        """매수 시그널: RSI 과매도"""
        rsi = data.get('rsi', 50)
        current_price = data.get('current_price', 0)
        
        if rsi <= self.oversold:
            return Signal(
                SignalType.BUY,
                price=current_price,
                reason=f"RSI 과매도 ({rsi:.1f})",
                score=60 + (self.oversold - rsi)
            )
        
        return Signal(SignalType.NONE)
    
    def check_sell_signal(self, data: dict) -> Signal:
        """매도 시그널: RSI 과매수 또는 손절"""
        rsi = data.get('rsi', 50)
        current_price = data.get('current_price', 0)
        buy_price = data.get('buy_price', 0)
        
        if buy_price == 0:
            return Signal(SignalType.NONE)
        
        profit_rate = (current_price - buy_price) / buy_price * 100
        
        # 손절
        if profit_rate <= -self.loss_cut:
            return Signal(
                SignalType.SELL,
                price=current_price,
                reason=f"손절 ({profit_rate:.2f}%)"
            )
        
        # RSI 과매수
        if rsi >= self.overbought:
            return Signal(
                SignalType.SELL,
                price=current_price,
                reason=f"RSI 과매수 ({rsi:.1f})"
            )
        
        return Signal(SignalType.NONE)
    
    def get_params(self) -> dict:
        return {
            'rsi_period': self.rsi_period,
            'oversold': self.oversold,
            'overbought': self.overbought,
            'loss_cut': self.loss_cut
        }
    
    def set_params(self, params: dict):
        self.rsi_period = params.get('rsi_period', self.rsi_period)
        self.oversold = params.get('oversold', self.oversold)
        self.overbought = params.get('overbought', self.overbought)
        self.loss_cut = params.get('loss_cut', self.loss_cut)


# 전략 레지스트리
AVAILABLE_STRATEGIES = {
    'volatility_breakout': VolatilityBreakout,
    'golden_cross': GoldenCross,
    'grid_trading': GridTrading,
    'rsi_reversal': RSIStrategy,
}

def get_strategy(strategy_name: str) -> Optional[BaseStrategy]:
    """전략 인스턴스 반환"""
    strategy_class = AVAILABLE_STRATEGIES.get(strategy_name)
    if strategy_class:
        return strategy_class()
    return None

def get_strategy_list() -> list:
    """사용 가능한 전략 목록 반환"""
    return [
        {'key': key, 'name': cls.name, 'description': cls.description}
        for key, cls in AVAILABLE_STRATEGIES.items()
    ]
