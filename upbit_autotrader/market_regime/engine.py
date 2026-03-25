"""Market regime scoring helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


@dataclass
class MarketRegimeSnapshot:
    as_of: str = ""
    local_breadth_score: float = 50.0
    btc_trend_vol_score: float = 50.0
    fear_greed_score: Optional[float] = None
    etf_flow_score: Optional[float] = None
    btc_dominance_score: Optional[float] = None
    stale_components: list[str] = field(default_factory=list)
    source_status: Dict[str, str] = field(default_factory=dict)


@dataclass
class MarketRegimeOutput:
    market_regime_score: float
    risk_multiplier: float
    label: str
    stale_components: list[str] = field(default_factory=list)
    details: Dict[str, float] = field(default_factory=dict)


def _weighted_score(components: list[tuple[str, Optional[float], float]], stale_components: list[str]) -> float:
    active: list[tuple[float, float]] = []
    stale = set(str(name) for name in stale_components)
    for name, score, weight in components:
        if score is None or name in stale:
            continue
        active.append((_clamp(score, 0.0, 100.0), float(weight)))
    if not active:
        return 50.0
    total_weight = sum(weight for _, weight in active)
    if total_weight <= 0:
        return 50.0
    return sum(score * weight for score, weight in active) / total_weight


def compute_phase1_score(snapshot: MarketRegimeSnapshot) -> float:
    return _weighted_score(
        [
            ("local_breadth", snapshot.local_breadth_score, 0.40),
            ("btc_trend_vol", snapshot.btc_trend_vol_score, 0.35),
            ("fear_greed", snapshot.fear_greed_score, 0.25),
        ],
        snapshot.stale_components,
    )


def compute_overlay_score(snapshot: MarketRegimeSnapshot) -> Optional[float]:
    if snapshot.etf_flow_score is None and snapshot.btc_dominance_score is None:
        return None
    return _weighted_score(
        [
            ("etf_flow", snapshot.etf_flow_score, 0.60),
            ("btc_dominance", snapshot.btc_dominance_score, 0.40),
        ],
        snapshot.stale_components,
    )


def merge_market_regime_scores(
    phase1_score: float,
    overlay_score: Optional[float],
    *,
    use_overlay: bool = False,
) -> float:
    phase1 = _clamp(phase1_score, 0.0, 100.0)
    if not use_overlay or overlay_score is None:
        return phase1
    return _clamp((0.85 * phase1) + (0.15 * _clamp(overlay_score, 0.0, 100.0)), 0.0, 100.0)


def resolve_market_regime_label_and_multiplier(score: float) -> tuple[str, float]:
    score = _clamp(score, 0.0, 100.0)
    if score < 40.0:
        return "defensive", 0.50
    if score < 55.0:
        return "neutral", 0.75
    if score < 70.0:
        return "risk_on", 1.00
    return "risk_on", 1.15


def build_market_regime_output(
    snapshot: MarketRegimeSnapshot,
    *,
    use_overlay: bool = False,
) -> MarketRegimeOutput:
    phase1_score = compute_phase1_score(snapshot)
    overlay_score = compute_overlay_score(snapshot)
    final_score = merge_market_regime_scores(phase1_score, overlay_score, use_overlay=use_overlay)
    label, multiplier = resolve_market_regime_label_and_multiplier(final_score)
    return MarketRegimeOutput(
        market_regime_score=final_score,
        risk_multiplier=multiplier,
        label=label,
        stale_components=list(snapshot.stale_components),
        details={
            "phase1_score": float(phase1_score),
            "overlay_score": float(overlay_score) if overlay_score is not None else 50.0,
            "local_breadth_score": float(snapshot.local_breadth_score),
            "btc_trend_vol_score": float(snapshot.btc_trend_vol_score),
            "fear_greed_score": float(snapshot.fear_greed_score) if snapshot.fear_greed_score is not None else 50.0,
            "etf_flow_score": float(snapshot.etf_flow_score) if snapshot.etf_flow_score is not None else 50.0,
            "btc_dominance_score": float(snapshot.btc_dominance_score) if snapshot.btc_dominance_score is not None else 50.0,
        },
    )


def build_neutral_market_regime_output() -> MarketRegimeOutput:
    return MarketRegimeOutput(
        market_regime_score=50.0,
        risk_multiplier=1.0,
        label="neutral",
        stale_components=[],
        details={"phase1_score": 50.0, "overlay_score": 50.0},
    )
