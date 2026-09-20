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

from upbit_autotrader.market_regime.engine import MarketRegimeSnapshot
from upbit_autotrader.services.rate_limit import RateLimitState, is_rate_limit_error



def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _parse_paren_number(text: str) -> Optional[float]:
    raw = str(text or "").strip().replace(",", "")
    if not raw:
        return None
    if raw.startswith("(") and raw.endswith(")"):
        return -_safe_float(raw[1:-1], 0.0)
    try:
        return float(raw)
    except ValueError:
        return None


def _extract_first_numeric(payload: Any, candidates: tuple[str, ...]) -> Optional[float]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_l = str(key).lower()
            if key_l in candidates:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    pass
            nested = _extract_first_numeric(value, candidates)
            if nested is not None:
                return nested
    elif isinstance(payload, list):
        for row in payload:
            nested = _extract_first_numeric(row, candidates)
            if nested is not None:
                return nested
    return None


@dataclass
class ProviderResult:
    score: Optional[float]
    status: str
    raw_value: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
