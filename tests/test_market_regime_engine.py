import pytest

from upbit_autotrader.market_regime.engine import (
    MarketRegimeSnapshot,
    build_neutral_market_regime_output,
    compute_overlay_score,
    compute_phase1_score,
    merge_market_regime_scores,
    resolve_market_regime_label_and_multiplier,
)


def test_phase1_score_reweights_stale_components():
    snapshot = MarketRegimeSnapshot(
        local_breadth_score=80.0,
        btc_trend_vol_score=20.0,
        fear_greed_score=100.0,
        stale_components=["fear_greed"],
    )
    assert compute_phase1_score(snapshot) == pytest.approx(52.0)


def test_overlay_score_reweights_stale_components():
    snapshot = MarketRegimeSnapshot(
        etf_flow_score=70.0,
        btc_dominance_score=30.0,
        stale_components=["btc_dominance"],
    )
    assert compute_overlay_score(snapshot) == pytest.approx(70.0)


def test_merge_market_regime_scores_applies_overlay_weight():
    assert merge_market_regime_scores(60.0, 80.0, use_overlay=True) == pytest.approx(63.0)
    assert merge_market_regime_scores(60.0, 80.0, use_overlay=False) == pytest.approx(60.0)


@pytest.mark.parametrize(
    ("score", "label", "multiplier"),
    [
        (35.0, "defensive", 0.50),
        (50.0, "neutral", 0.75),
        (60.0, "risk_on", 1.00),
        (80.0, "risk_on", 1.15),
    ],
)
def test_resolve_market_regime_label_and_multiplier_boundaries(score, label, multiplier):
    resolved_label, resolved_multiplier = resolve_market_regime_label_and_multiplier(score)
    assert resolved_label == label
    assert resolved_multiplier == pytest.approx(multiplier)


def test_build_neutral_market_regime_output_uses_startup_defaults():
    out = build_neutral_market_regime_output()
    assert out.market_regime_score == pytest.approx(50.0)
    assert out.label == "neutral"
    assert out.risk_multiplier == pytest.approx(1.0)
