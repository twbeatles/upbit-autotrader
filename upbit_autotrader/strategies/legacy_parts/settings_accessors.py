from __future__ import annotations

# Runtime bindings injected by legacy_strategy facade
Config = None
pd = None
pyupbit = None
datetime = None
time = None


def bind_runtime(**kwargs):
    globals().update(kwargs)



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


def _get_interval_cache_ttl(self, interval: str) -> float:
    ttl_map = getattr(Config, "INDICATOR_CACHE_TTL_BY_INTERVAL", {})
    return float(ttl_map.get(interval, 5))
