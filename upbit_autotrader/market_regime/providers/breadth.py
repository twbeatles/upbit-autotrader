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
from .base import ProviderResult, _clamp, _safe_float



class UpbitMarketBreadthProvider:
    MARKET_ALL_URL = "https://api.upbit.com/v1/market/all"
    TICKER_URL = "https://api.upbit.com/v1/ticker"

    def __init__(self, session: Any = None, timeout: int = 10, candle_request_delay_sec: float = 0.11):
        self.session = session or requests
        self.timeout = int(timeout)
        self.candle_request_delay_sec = max(0.0, float(candle_request_delay_sec))
        self.rate_limit_state = RateLimitState(min_interval_by_group={"quotation": self.candle_request_delay_sec})

    def _get(self, url: str, **kwargs: Any):
        self.rate_limit_state.wait_before_call("quotation", default_interval=self.candle_request_delay_sec)
        try:
            response = self.session.get(url, **kwargs)
        except Exception as exc:
            if is_rate_limit_error(exc):
                self.rate_limit_state.penalize("quotation", seconds=1.0)
            raise
        self.rate_limit_state.mark_call("quotation")
        self.rate_limit_state.observe_response("quotation", response)
        return response

    def _fetch_krw_markets(self) -> list[str]:
        response = self._get(
            self.MARKET_ALL_URL,
            params={"isDetails": "false"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return []
        return [
            str(row.get("market") or "").strip()
            for row in payload
            if isinstance(row, dict) and str(row.get("market") or "").startswith("KRW-")
        ]

    def _fetch_ticker_rows(self, markets: list[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for idx in range(0, len(markets), 100):
            chunk = markets[idx : idx + 100]
            if not chunk:
                continue
            response = self._get(
                self.TICKER_URL,
                params={"markets": ",".join(chunk)},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list):
                rows.extend(row for row in payload if isinstance(row, dict))
        return rows

    def fetch(self, *, top_n: int = 20, interval: str = "minute240") -> ProviderResult:
        _pyupbit = _resolve_pyupbit()
        if _pyupbit is None:
            return ProviderResult(None, "error", details={"reason": "pyupbit_unavailable"})
        try:
            markets = self._fetch_krw_markets()
            ticker_rows = self._fetch_ticker_rows(markets)
        except Exception as exc:
            return ProviderResult(None, "error", details={"reason": str(exc)})

        ranked = sorted(
            ticker_rows,
            key=lambda row: _safe_float(row.get("acc_trade_price_24h"), 0.0),
            reverse=True,
        )
        selected = [str(row.get("market") or "") for row in ranked[: max(1, int(top_n))]]

        sample_count = 0
        above_ma_count = 0
        positive_count = 0
        for market in selected:
            try:
                df = _pyupbit.get_ohlcv(market, interval=interval, count=30)
            except Exception:
                if self.candle_request_delay_sec > 0:
                    time.sleep(self.candle_request_delay_sec)
                continue
            if self.candle_request_delay_sec > 0:
                time.sleep(self.candle_request_delay_sec)
            if df is None or len(df) < 21:
                continue
            close = df["close"]
            ma20 = float(close.rolling(window=20).mean().iloc[-1])
            current = float(close.iloc[-1])
            previous = float(close.iloc[-2])
            sample_count += 1
            if current >= ma20:
                above_ma_count += 1
            if current > previous:
                positive_count += 1

        if sample_count <= 0:
            return ProviderResult(None, "error", details={"reason": "no_valid_samples"})

        above_ma_ratio = above_ma_count / sample_count
        positive_ratio = positive_count / sample_count
        score = (60.0 * above_ma_ratio) + (40.0 * positive_ratio)
        return ProviderResult(
            _clamp(score, 0.0, 100.0),
            "ok",
            raw_value=float(score),
            details={
                "sample_count": sample_count,
                "above_ma_ratio": above_ma_ratio,
                "positive_ratio": positive_ratio,
            },
        )
