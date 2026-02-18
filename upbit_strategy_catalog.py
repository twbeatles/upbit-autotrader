"""Strategy catalog metadata for Upbit Pro Algo-Trader."""

from typing import Dict, Any


STRATEGY_CATALOG: Dict[str, Dict[str, Any]] = {
    "volatility_breakout": {
        "name": "변동성 돌파",
        "category": "trend",
        "tradeable": True,
        "default_weight": 1.0,
        "params": {"min_score": 55},
        "description": "목표가/MA 돌파 기반 추세 진입",
    },
    "donchian_breakout": {
        "name": "돈치안 돌파",
        "category": "trend",
        "tradeable": True,
        "default_weight": 1.0,
        "params": {"channel_period": 20, "min_score": 55},
        "description": "N-채널 상단 돌파 진입",
    },
    "ema_cross_trend": {
        "name": "EMA 크로스",
        "category": "trend",
        "tradeable": True,
        "default_weight": 1.0,
        "params": {"fast": 12, "slow": 26, "min_score": 55},
        "description": "EMA 골든크로스 + 기울기 확인",
    },
    "time_series_momentum": {
        "name": "시계열 모멘텀",
        "category": "momentum",
        "tradeable": True,
        "default_weight": 1.0,
        "params": {"lookback": 20, "threshold_pct": 1.0, "min_score": 55},
        "description": "룩백 수익률 임계값 기반",
    },
    "rsi_reversion": {
        "name": "RSI 평균회귀",
        "category": "mean_reversion",
        "tradeable": True,
        "default_weight": 1.0,
        "params": {"oversold": 30, "exit_rsi": 55, "min_score": 55},
        "description": "과매도 반등 진입/중립구간 청산",
    },
    "bollinger_reversion": {
        "name": "볼린저 평균회귀",
        "category": "mean_reversion",
        "tradeable": True,
        "default_weight": 1.0,
        "params": {"entry_band": 1.0, "exit_to_mid": True, "min_score": 55},
        "description": "하단 밴드 이탈-복귀 진입",
    },
    "zscore_reversion": {
        "name": "Z-Score 평균회귀",
        "category": "mean_reversion",
        "tradeable": True,
        "default_weight": 1.0,
        "params": {"entry_z": -1.8, "exit_z": -0.3, "min_score": 55},
        "description": "롤링 평균/표준편차 편차 기반",
    },
    "volatility_targeting": {
        "name": "변동성 타게팅",
        "category": "risk",
        "tradeable": True,
        "default_weight": 1.0,
        "params": {"target_vol_pct": 2.0, "max_scale": 1.8, "min_scale": 0.4},
        "description": "실현변동성 대비 포지션 크기 조절",
    },
    "regime_filter": {
        "name": "레짐 필터",
        "category": "risk",
        "tradeable": True,
        "default_weight": 1.0,
        "params": {"min_adx": 18},
        "description": "ADX/MTF로 추세 장세만 필터링",
    },
    "drawdown_guard": {
        "name": "드로우다운 가드",
        "category": "risk",
        "tradeable": True,
        "default_weight": 1.0,
        "params": {"max_daily_loss_pct": 5.0, "max_consecutive_losses": 3},
        "description": "세션 손실/연속 손실 제한",
    },
    "pairs_trading_research": {
        "name": "페어트레이딩(연구)",
        "category": "research",
        "tradeable": False,
        "default_weight": 0.0,
        "params": {},
        "description": "현 구조에서는 백테스트 연구 전용",
    },
}


def get_tradeable_strategy_ids():
    return [sid for sid, meta in STRATEGY_CATALOG.items() if meta.get("tradeable")]


def get_default_weights():
    return {
        sid: float(meta.get("default_weight", 1.0))
        for sid, meta in STRATEGY_CATALOG.items()
        if meta.get("tradeable") and meta.get("category") not in {"risk", "research"}
    }


def get_default_active_strategies():
    return list(get_default_weights().keys())
