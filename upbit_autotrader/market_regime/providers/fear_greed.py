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
from .base import ProviderResult, _clamp, _safe_float



class AlternativeFearGreedProvider:
    URL = "https://api.alternative.me/fng/"

    def __init__(self, session: Any = None, timeout: int = 10, max_age_hours: float = 12.0):
        self.session = session or requests
        self.timeout = int(timeout)
        self.max_age_hours = float(max_age_hours)

    def fetch(self) -> ProviderResult:
        try:
            response = self.session.get(
                self.URL,
                params={"limit": 1, "format": "json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            row = (payload.get("data") or [None])[0]
        except Exception as exc:
            return ProviderResult(None, "error", details={"reason": str(exc)})

        if not isinstance(row, dict):
            return ProviderResult(None, "error", details={"reason": "invalid_fng_payload"})

        score = _clamp(_safe_float(row.get("value"), 50.0), 0.0, 100.0)
        timestamp_raw = str(row.get("timestamp") or "").strip()
        try:
            updated_at = _dt.datetime.fromtimestamp(float(timestamp_raw), tz=_dt.timezone.utc)
            age_hours = max(0.0, (_dt.datetime.now(tz=_dt.timezone.utc) - updated_at).total_seconds() / 3600.0)
        except Exception:
            age_hours = self.max_age_hours + 1.0

        status = "ok" if age_hours <= self.max_age_hours else "stale"
        return ProviderResult(
            score,
            status,
            raw_value=score,
            details={"age_hours": age_hours, "classification": str(row.get("value_classification") or "")},
        )
