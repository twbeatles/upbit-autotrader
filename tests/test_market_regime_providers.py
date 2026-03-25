import datetime as dt
import types

import pandas as pd
import pytest

from upbit_autotrader.market_regime import providers
from upbit_autotrader.market_regime.providers import ProviderResult


class _Response:
    def __init__(self, *, payload=None, text="", status_code=200):
        self._payload = payload
        self.text = text
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")


class _Session:
    def __init__(self, handlers):
        self.handlers = handlers

    def get(self, url, params=None, timeout=None):
        handler = self.handlers[url]
        return handler(params, timeout) if callable(handler) else handler


def _frame(values):
    return pd.DataFrame(
        {
            "open": list(values),
            "high": list(values),
            "low": list(values),
            "close": list(values),
            "volume": [1.0] * len(list(values)),
        }
    )


def test_upbit_market_breadth_provider_scores_top_n(monkeypatch):
    frames = {
        "KRW-B": _frame(range(1, 31)),
        "KRW-C": _frame(range(30, 0, -1)),
    }
    monkeypatch.setattr(
        providers,
        "pyupbit",
        types.SimpleNamespace(get_ohlcv=lambda market, interval="minute240", count=30: frames[market]),
    )
    session = _Session(
        {
            providers.UpbitMarketBreadthProvider.MARKET_ALL_URL: _Response(
                payload=[{"market": "KRW-A"}, {"market": "KRW-B"}, {"market": "KRW-C"}]
            ),
            providers.UpbitMarketBreadthProvider.TICKER_URL: _Response(
                payload=[
                    {"market": "KRW-A", "acc_trade_price_24h": 100.0},
                    {"market": "KRW-B", "acc_trade_price_24h": 300.0},
                    {"market": "KRW-C", "acc_trade_price_24h": 200.0},
                ]
            ),
        }
    )

    out = providers.UpbitMarketBreadthProvider(session=session).fetch(top_n=2)

    assert out.status == "ok"
    assert out.details["sample_count"] == 2
    assert out.score == pytest.approx(50.0)


def test_alternative_fear_greed_provider_marks_stale_when_age_exceeds_limit():
    old_ts = int((dt.datetime.now(tz=dt.timezone.utc) - dt.timedelta(hours=30)).timestamp())
    session = _Session(
        {
            providers.AlternativeFearGreedProvider.URL: _Response(
                payload={
                    "data": [
                        {
                            "value": "72",
                            "timestamp": str(old_ts),
                            "value_classification": "Greed",
                        }
                    ]
                }
            )
        }
    )

    out = providers.AlternativeFearGreedProvider(session=session, max_age_hours=12.0).fetch()

    assert out.status == "stale"
    assert out.score == pytest.approx(72.0)


def test_alternative_global_provider_extracts_btc_dominance():
    session = _Session(
        {
            providers.AlternativeGlobalProvider.URL: _Response(
                payload={"data": {"quotes": {"USD": {}}, "btc_dominance_percentage": 60.2}}
            )
        }
    )

    out = providers.AlternativeGlobalProvider(session=session).fetch()

    assert out.status == "ok"
    assert out.raw_value == pytest.approx(60.2)
    assert out.score == pytest.approx(55.0)


def test_farside_etf_flow_provider_parses_recent_total():
    html = """
    <table>
      <tr><th>Date</th><th>Total</th></tr>
      <tr><td>19 Mar 2026</td><td>10</td></tr>
      <tr><td>20 Mar 2026</td><td>20</td></tr>
      <tr><td>21 Mar 2026</td><td>(5)</td></tr>
    </table>
    """
    session = _Session({providers.FarsideEtfFlowProvider.URL: _Response(text=html)})

    out = providers.FarsideEtfFlowProvider(session=session, days=3).fetch()

    assert out.status == "ok"
    assert out.raw_value == pytest.approx(25.0)
    assert out.score == pytest.approx(70.0)


def test_build_market_regime_snapshot_preserves_fallback_scores_for_failed_sources(monkeypatch):
    class _StubProvider:
        def __init__(self, result):
            self.result = result

        def fetch(self, *args, **kwargs):
            return self.result

    monkeypatch.setattr(
        providers,
        "UpbitMarketBreadthProvider",
        lambda: _StubProvider(ProviderResult(62.0, "ok")),
    )
    monkeypatch.setattr(
        providers,
        "BtcTrendVolProvider",
        lambda: _StubProvider(ProviderResult(None, "error")),
    )
    monkeypatch.setattr(
        providers,
        "AlternativeFearGreedProvider",
        lambda: _StubProvider(ProviderResult(44.0, "stale")),
    )
    monkeypatch.setattr(
        providers,
        "FarsideEtfFlowProvider",
        lambda: _StubProvider(ProviderResult(None, "error")),
    )
    monkeypatch.setattr(
        providers,
        "AlternativeGlobalProvider",
        lambda: _StubProvider(ProviderResult(55.0, "ok")),
    )

    snapshot = providers.build_market_regime_snapshot(top_n=5, use_fear_greed=True, use_etf_flow=True)

    assert snapshot.local_breadth_score == pytest.approx(62.0)
    assert snapshot.btc_trend_vol_score == pytest.approx(50.0)
    assert snapshot.fear_greed_score == pytest.approx(44.0)
    assert snapshot.etf_flow_score == pytest.approx(50.0)
    assert snapshot.btc_dominance_score == pytest.approx(55.0)
    assert set(snapshot.stale_components) == {"btc_trend_vol", "fear_greed", "etf_flow"}
