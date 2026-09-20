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
from .base import ProviderResult




def build_market_regime_snapshot(
    *,
    top_n: int = 20,
    use_fear_greed: bool = True,
    use_etf_flow: bool = False,
) -> MarketRegimeSnapshot:
    from upbit_autotrader.market_regime import providers as _providers  # lazy: respects monkeypatch
    UpbitMarketBreadthProvider = _providers.UpbitMarketBreadthProvider
    BtcTrendVolProvider = _providers.BtcTrendVolProvider
    AlternativeFearGreedProvider = _providers.AlternativeFearGreedProvider
    AlternativeGlobalProvider = _providers.AlternativeGlobalProvider
    FarsideEtfFlowProvider = _providers.FarsideEtfFlowProvider
    stale_components: list[str] = []
    source_status: dict[str, str] = {}

    breadth_result = UpbitMarketBreadthProvider().fetch(top_n=top_n)
    btc_result = BtcTrendVolProvider().fetch()

    source_status["local_breadth"] = breadth_result.status
    source_status["btc_trend_vol"] = btc_result.status
    if breadth_result.status != "ok":
        stale_components.append("local_breadth")
    if btc_result.status != "ok":
        stale_components.append("btc_trend_vol")

    fear_greed_score: Optional[float] = None
    if use_fear_greed:
        fear_result = AlternativeFearGreedProvider().fetch()
        source_status["fear_greed"] = fear_result.status
        fear_greed_score = fear_result.score
        if fear_result.status != "ok":
            stale_components.append("fear_greed")
    else:
        source_status["fear_greed"] = "disabled"

    etf_flow_score: Optional[float] = None
    btc_dominance_score: Optional[float] = None
    if use_etf_flow:
        etf_result = FarsideEtfFlowProvider().fetch()
        dom_result = AlternativeGlobalProvider().fetch()
        source_status["etf_flow"] = etf_result.status
        source_status["btc_dominance"] = dom_result.status
        etf_flow_score = etf_result.score
        btc_dominance_score = dom_result.score
        if etf_result.status != "ok":
            stale_components.append("etf_flow")
        if dom_result.status != "ok":
            stale_components.append("btc_dominance")
    else:
        source_status["etf_flow"] = "disabled"
        source_status["btc_dominance"] = "disabled"

    return MarketRegimeSnapshot(
        as_of=_dt.datetime.now(tz=_dt.timezone.utc).isoformat(),
        local_breadth_score=float(breadth_result.score if breadth_result.score is not None else 50.0),
        btc_trend_vol_score=float(btc_result.score if btc_result.score is not None else 50.0),
        fear_greed_score=None if not use_fear_greed else (float(fear_greed_score) if fear_greed_score is not None else 50.0),
        etf_flow_score=None if not use_etf_flow else (float(etf_flow_score) if etf_flow_score is not None else 50.0),
        btc_dominance_score=None if not use_etf_flow else (float(btc_dominance_score) if btc_dominance_score is not None else 50.0),
        stale_components=sorted(set(stale_components)),
        source_status=source_status,
    )
