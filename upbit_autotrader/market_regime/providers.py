"""External and local market regime data providers."""

from __future__ import annotations

import datetime as _dt
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Dict, Optional

import requests

try:
    import pyupbit
except ImportError:  # pragma: no cover - handled in callers/tests
    pyupbit = None

from upbit_autotrader.market_regime.engine import MarketRegimeSnapshot


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


class UpbitMarketBreadthProvider:
    MARKET_ALL_URL = "https://api.upbit.com/v1/market/all"
    TICKER_URL = "https://api.upbit.com/v1/ticker"

    def __init__(self, session: Any = None, timeout: int = 10):
        self.session = session or requests
        self.timeout = int(timeout)

    def _fetch_krw_markets(self) -> list[str]:
        response = self.session.get(
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
            response = self.session.get(
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
        if pyupbit is None:
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
                df = pyupbit.get_ohlcv(market, interval=interval, count=30)
            except Exception:
                continue
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


class BtcTrendVolProvider:
    def fetch(self, *, interval: str = "minute240") -> ProviderResult:
        if pyupbit is None:
            return ProviderResult(None, "error", details={"reason": "pyupbit_unavailable"})
        try:
            df = pyupbit.get_ohlcv("KRW-BTC", interval=interval, count=30)
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


class _FarsideTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self._in_row = False
        self._in_cell = False
        self._cell_parts: list[str] = []
        self._current_row: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag == "tr":
            self._in_row = True
            self._current_row = []
        elif self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._cell_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._in_cell and tag in {"td", "th"}:
            value = "".join(self._cell_parts).strip()
            self._current_row.append(re.sub(r"\s+", " ", value))
            self._cell_parts = []
            self._in_cell = False
        elif self._in_row and tag == "tr":
            if self._current_row:
                self.rows.append(self._current_row)
            self._current_row = []
            self._in_row = False


class FarsideEtfFlowProvider:
    URL = "https://farside.co.uk/btc"
    DATE_RE = re.compile(r"^\d{1,2} [A-Za-z]{3} \d{4}$")

    def __init__(self, session: Any = None, timeout: int = 10, days: int = 3):
        self.session = session or requests
        self.timeout = int(timeout)
        self.days = max(1, int(days))

    @staticmethod
    def _total_to_score(total_flow_musd: float) -> float:
        if total_flow_musd > 0:
            return 70.0
        if total_flow_musd < 0:
            return 30.0
        return 50.0

    def fetch(self) -> ProviderResult:
        try:
            response = self.session.get(self.URL, timeout=self.timeout)
            response.raise_for_status()
            parser = _FarsideTableParser()
            parser.feed(response.text)
        except Exception as exc:
            return ProviderResult(None, "error", details={"reason": str(exc)})

        dated_rows: list[tuple[_dt.datetime, float]] = []
        for row in parser.rows:
            if not row or not self.DATE_RE.match(str(row[0] or "").strip()):
                continue
            total_value = None
            for cell in reversed(row[1:]):
                total_value = _parse_paren_number(cell)
                if total_value is not None:
                    break
            if total_value is None:
                continue
            try:
                parsed_date = _dt.datetime.strptime(str(row[0]), "%d %b %Y")
            except ValueError:
                continue
            dated_rows.append((parsed_date, float(total_value)))

        if not dated_rows:
            return ProviderResult(None, "error", details={"reason": "missing_farside_rows"})

        dated_rows.sort(key=lambda item: item[0])
        recent = dated_rows[-self.days :]
        total_flow = sum(value for _, value in recent)
        return ProviderResult(
            self._total_to_score(total_flow),
            "ok",
            raw_value=total_flow,
            details={"days": len(recent), "total_flow_musd": total_flow},
        )


def build_market_regime_snapshot(
    *,
    top_n: int = 20,
    use_fear_greed: bool = True,
    use_etf_flow: bool = False,
) -> MarketRegimeSnapshot:
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
