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
from .base import ProviderResult, _extract_first_numeric



class AlternativeGlobalProvider:
    URL = "https://api.alternative.me/v2/global/"

    def __init__(self, session: Any = None, timeout: int = 10):
        self.session = session or requests
        self.timeout = int(timeout)

    @staticmethod
    def _dominance_to_score(dominance: float) -> float:
        if dominance < 50.0:
            return 45.0
        if dominance < 58.0:
            return 60.0
        if dominance <= 62.0:
            return 55.0
        return 40.0

    def fetch(self) -> ProviderResult:
        try:
            response = self.session.get(self.URL, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            return ProviderResult(None, "error", details={"reason": str(exc)})

        dominance = _extract_first_numeric(
            payload,
            (
                "bitcoin_percentage_of_market_cap",
                "btc_dominance",
                "btc_dominance_percentage",
                "btc",
            ),
        )
        if dominance is None:
            return ProviderResult(None, "error", details={"reason": "missing_btc_dominance"})
        score = self._dominance_to_score(float(dominance))
        return ProviderResult(score, "ok", raw_value=float(dominance), details={"btc_dominance": float(dominance)})
