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

from upbit_autotrader.core.config import Config
from upbit_autotrader.strategies.legacy_parts import controls_ops as _legacy_controls, context_ops as _legacy_context, entry_ops as _legacy_entry, indicators as _legacy_indicators, settings_accessors as _legacy_accessors


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
        self._trend_cache = {}  # {(ticker, interval, period): {"ts": float, "trend": str}}
        
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
        _legacy_indicators.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_indicators.calculate_target_price(self, ticker, interval)
    
    def calculate_ma(self, ticker: str, interval: str, period: int = 5) -> Optional[float]:
        """이동평균 계산"""
        _legacy_indicators.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_indicators.calculate_ma(self, ticker, interval, period)
    
    def calculate_rsi(self, ticker: str, period: int = 14) -> float:
        """RSI 계산"""
        _legacy_indicators.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_indicators.calculate_rsi(self, ticker, period)
    
    def calculate_macd(self, ticker: str) -> Tuple[float, float, float]:
        """MACD 계산 (MACD, Signal, Histogram 반환)"""
        _legacy_indicators.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_indicators.calculate_macd(self, ticker)
    
    def calculate_bollinger_bands(self, ticker: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """볼린저 밴드 계산 (상단, 중간, 하단 반환)"""
        _legacy_indicators.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_indicators.calculate_bollinger_bands(self, ticker)
    
    def calculate_atr(self, ticker: str, period: int = 14) -> Optional[float]:
        """ATR (Average True Range) 계산"""
        _legacy_indicators.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_indicators.calculate_atr(self, ticker, period)
    
    def calculate_volume_avg(self, ticker: str, period: int = 20) -> Tuple[Optional[float], Optional[float]]:
        """평균 거래량 계산"""
        _legacy_indicators.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_indicators.calculate_volume_avg(self, ticker, period)
    
    def calculate_stoch_rsi(
        self,
        ticker: str,
        rsi_period: int = 14,
        stoch_period: int = 14,
        k_period: int = 3,
        d_period: int = 3,
    ) -> Tuple[float, float]:
        """스토캐스틱 RSI 계산"""
        _legacy_indicators.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_indicators.calculate_stoch_rsi(self, ticker, rsi_period, stoch_period, k_period, d_period)
    
    def calculate_dmi_adx(self, ticker: str, period: int = 14) -> Tuple[float, float, float]:
        """DMI와 ADX 계산 - 추세 강도 측정"""
        _legacy_indicators.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_indicators.calculate_dmi_adx(self, ticker, period)
    
    def calculate_entry_score(self, ticker: str, curr_price: float, info: Dict) -> Tuple[int, List[str]]:
        """진입 점수 계산 (0~100점)"""
        _legacy_entry.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_entry.calculate_entry_score(self, ticker, curr_price, info)
    
    # =========================================================================
    # v3.0 고급 기능: 재진입 쿨다운
    # =========================================================================
    def set_cooldown(self, ticker: str, minutes: int = None):
        """매도 후 재진입 쿨다운 설정"""
        _legacy_controls.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_controls.set_cooldown(self, ticker, minutes)
    
    def check_cooldown(self, ticker: str) -> bool:
        """쿨다운 상태 확인 (True = 매수 가능)"""
        _legacy_controls.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_controls.check_cooldown(self, ticker)
    
    def clear_cooldown(self, ticker: str):
        """쿨다운 해제"""
        _legacy_controls.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_controls.clear_cooldown(self, ticker)
    
    # =========================================================================
    # v3.0 고급 기능: 시간 기반 청산
    # =========================================================================
    def set_holding_start(self, ticker: str):
        """보유 시작 시간 기록"""
        _legacy_controls.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_controls.set_holding_start(self, ticker)
    
    def check_holding_time_exit(self, ticker: str, max_hours: int = None) -> bool:
        """보유 시간 초과 시 청산 필요 여부"""
        _legacy_controls.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_controls.check_holding_time_exit(self, ticker, max_hours)
    
    def clear_holding_start(self, ticker: str):
        """보유 시간 기록 삭제"""
        _legacy_controls.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_controls.clear_holding_start(self, ticker)
    
    # =========================================================================
    # v3.0 고급 기능: 동적 포지션 사이징 (Anti-Martingale)
    # =========================================================================
    def calculate_dynamic_position_size(self, ticker: str) -> float:
        """연속 손익에 따른 포지션 크기 조정"""
        _legacy_controls.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_controls.calculate_dynamic_position_size(self, ticker)
    
    def update_consecutive_results(self, is_profit: bool):
        """연속 손익 결과 업데이트"""
        _legacy_controls.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_controls.update_consecutive_results(self, is_profit)
    
    def reset_consecutive_results(self):
        """연속 손익 초기화"""
        _legacy_controls.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_controls.reset_consecutive_results(self)
    
    # =========================================================================
    # v3.0 고급 기능: MTF (다중 시간프레임) 분석
    # =========================================================================
    def check_mtf_condition(self, ticker: str) -> bool:
        """일봉과 단기봉의 추세가 일치할 때만 매수"""
        _legacy_context.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_context.check_mtf_condition(self, ticker)
    
    def _get_trend(self, ticker: str, interval: str, period: int = 5) -> str:
        """추세 판단 (UP/DOWN/SIDEWAYS)"""
        _legacy_context.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_context._get_trend(self, ticker, interval, period)
    
    # =========================================================================
    # v3.0 고급 기능: 갭 분석
    # =========================================================================
    def analyze_gap(self, ticker: str) -> Tuple[str, float]:
        """시가갭 분석

Returns:
    (갭 유형, 갭 비율%)
    갭 유형: 'gap_up', 'gap_down', 'no_gap'"""
        _legacy_context.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_context.analyze_gap(self, ticker)
    
    def get_gap_adjusted_k(self, ticker: str, base_k: float) -> float:
        """갭에 따른 K값 조정"""
        _legacy_context.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_context.get_gap_adjusted_k(self, ticker, base_k)
    
    # =========================================================================
    # v3.0 고급 기능: 돌파 확인 (N틱 유지)
    # =========================================================================
    def update_recent_price(self, ticker: str, price: float):
        """최근 가격 업데이트"""
        _legacy_context.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_context.update_recent_price(self, ticker, price)
    
    def check_breakout_confirmation(
        self,
        ticker: str,
        target_price: float,
        confirm_ticks: int = None,
    ) -> bool:
        """목표가 돌파 후 N틱 유지 확인"""
        _legacy_context.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_context.check_breakout_confirmation(self, ticker, target_price, confirm_ticks)
    
    def clear_recent_prices(self, ticker: str):
        """최근 가격 기록 삭제"""
        _legacy_context.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_context.clear_recent_prices(self, ticker)
    
    # =========================================================================
    # v3.0 고급 기능: 분할 익절 추적
    # =========================================================================
    def check_partial_take_profit(self, ticker: str, profit_rate: float) -> Optional[Dict]:
        """단계별 익절 조건 확인

Returns:
    {'sell_ratio': 매도비율, 'level': 단계, 'rate': 수익률} 또는 None"""
        _legacy_controls.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_controls.check_partial_take_profit(self, ticker, profit_rate)
    
    def mark_partial_profit_executed(self, ticker: str, level: float):
        """분할 익절 실행 표시"""
        _legacy_controls.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_controls.mark_partial_profit_executed(self, ticker, level)
    
    def clear_partial_profit(self, ticker: str):
        """분할 익절 기록 삭제"""
        _legacy_controls.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_controls.clear_partial_profit(self, ticker)
    
    # =========================================================================
    # 헬퍼 메서드들 (트레이더 UI 접근)
    # =========================================================================
    def _get_candle_interval(self) -> str:
        """현재 설정된 캔들 간격 조회"""
        _legacy_accessors.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_accessors._get_candle_interval(self)
    
    def _get_k_value(self) -> float:
        """K값 조회"""
        _legacy_accessors.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_accessors._get_k_value(self)
    
    def _get_betting_ratio(self) -> float:
        """베팅 비율 조회"""
        _legacy_accessors.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_accessors._get_betting_ratio(self)
    
    def _get_rsi_period(self) -> int:
        """RSI 기간 조회"""
        _legacy_accessors.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_accessors._get_rsi_period(self)
    
    def _get_volume_multiplier(self) -> float:
        """거래량 배수 조회"""
        _legacy_accessors.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_accessors._get_volume_multiplier(self)
    
    def _is_cooldown_enabled(self) -> bool:
        """쿨다운 활성화 여부"""
        _legacy_accessors.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_accessors._is_cooldown_enabled(self)
    
    def _is_time_exit_enabled(self) -> bool:
        """시간 청산 활성화 여부"""
        _legacy_accessors.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_accessors._is_time_exit_enabled(self)
    
    def _is_dynamic_position_enabled(self) -> bool:
        """동적 포지션 활성화 여부"""
        _legacy_accessors.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_accessors._is_dynamic_position_enabled(self)
    
    def _is_mtf_enabled(self) -> bool:
        """MTF 활성화 여부"""
        _legacy_accessors.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_accessors._is_mtf_enabled(self)
    
    def _is_gap_analysis_enabled(self) -> bool:
        """갭 분석 활성화 여부"""
        _legacy_accessors.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_accessors._is_gap_analysis_enabled(self)
    
    def _is_breakout_confirm_enabled(self) -> bool:
        """돌파 확인 활성화 여부"""
        _legacy_accessors.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_accessors._is_breakout_confirm_enabled(self)

    def _get_interval_cache_ttl(self, interval: str) -> float:
        _legacy_accessors.bind_runtime(
            Config=Config,
            pd=pd,
            pyupbit=pyupbit,
            datetime=datetime,
            time=time,
        )
        return _legacy_accessors._get_interval_cache_ttl(self, interval)

