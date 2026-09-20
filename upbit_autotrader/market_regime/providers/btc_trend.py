"""External and local market regime data providers."""

from __future__ import annotations

import datetime as _dt
import json
import re
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Dict, Optional

import requests

from upbit_autotrader.services.pyupbit_compat import pyupbit_fallback

try:
    import pyupbit
except ImportError:  # pragma: no cover - handled in callers/tests
    pyupbit = pyupbit_fallback


def _resolve_pyupbit():
    """Resolve pyupbit via package attr so tests can monkeypatch providers.pyupbit (compat)."""
    try:
        from upbit_autotrader.market_regime import providers as _pkg
        return _pkg.pyupbit
    except Exception:
        return pyupbit


from upbit_autotrader.market_regime.engine import MarketRegimeSnapshot
from upbit_autotrader.services.rate_limit import RateLimitState, is_rate_limit_error
from .base import ProviderResult, _clamp



class BtcTrendVolProvider:
    def fetch(self, *, interval: str = "minute240") -> ProviderResult:
        _pyupbit = _resolve_pyupbit()
        if _pyupbit is None:
            return ProviderResult(None, "error", details={"reason": "pyupbit_unavailable"})
        try:
            df = _pyupbit.get_ohlcv("KRW-BTC", interval=interval, count=30)
        except Exception as exc:
            return ProviderResult(None, "error", details={"reason": str(exc)})
        if df is None or len(df) < 26:
            return ProviderResult(None, "error", details={"reason": "insufficient_btc_history"})

        close = df["close"]
        ema_fast = close.ewm(span=12, adjust=False).mean()
        ema_slow = close.ewm(span=26, adjust=False).mean()
        trend_score = 55.0 if float(ema_fast.iloc[-1]) > float(ema_slow.iloc[-1]) else 20.0
        slope_score = 20.0 if float(ema_fast.iloc[-1]) > float(ema_fast.iloc[-2]) else 0.0

        realized_vol_pct = 0.0
        ret = close.pct_change().dropna()
        if len(ret) >= 20:
            realized_vol_pct = float(ret.iloc[-20:].std() * (20**0.5) * 100.0)

        if realized_vol_pct <= 4.0:
            vol_score = 25.0
        elif realized_vol_pct <= 6.0:
            vol_score = 15.0
        elif realized_vol_pct <= 8.0:
            vol_score = 5.0
        else:
            vol_score = 0.0

        score = trend_score + slope_score + vol_score
        return ProviderResult(
            _clamp(score, 0.0, 100.0),
            "ok",
            raw_value=realized_vol_pct,
            details={
                "trend_score": trend_score,
                "slope_score": slope_score,
                "vol_score": vol_score,
                "realized_vol_pct": realized_vol_pct,
            },
        )
