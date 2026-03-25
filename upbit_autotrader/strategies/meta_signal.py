"""Meta-signal and strategy performance utilities."""

import datetime
import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple, Optional


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


@dataclass
class StrategyPerformance:
    wins: int = 0
    losses: int = 0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    expectancy: float = 0.0
    sample_count: int = 0
    updated_at: str = ""


@dataclass
class MetaSignalInput:
    strategy_id: str
    engine_score: float
    technical_regime_score: float = 50.0
    market_regime_score: float = 50.0
    regime_score: Optional[float] = None
    min_expectancy: float = 0.0
    score_threshold: float = 60.0

    def __post_init__(self):
        if self.regime_score is not None:
            self.technical_regime_score = _safe_float(self.regime_score, self.technical_regime_score)


@dataclass
class MetaSignalOutput:
    strategy_id: str
    meta_score: float
    expected_value: float
    gate_pass: bool
    components: Dict[str, float]


class StrategyPerformanceTracker:
    def __init__(self):
        self.stats: Dict[str, StrategyPerformance] = {}
        self.last_rebalance_date: str = ""

    def get(self, strategy_id: str) -> StrategyPerformance:
        sid = str(strategy_id or "unknown")
        return self.stats.get(sid, StrategyPerformance())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stats": {sid: asdict(perf) for sid, perf in self.stats.items()},
            "last_rebalance_date": str(self.last_rebalance_date or ""),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]):
        inst = cls()
        rows = payload.get("stats", {}) if isinstance(payload, dict) else {}
        if isinstance(rows, dict):
            for sid, raw in rows.items():
                if not isinstance(raw, dict):
                    continue
                inst.stats[str(sid)] = StrategyPerformance(
                    wins=int(raw.get("wins", 0) or 0),
                    losses=int(raw.get("losses", 0) or 0),
                    avg_win_pct=_safe_float(raw.get("avg_win_pct"), 0.0),
                    avg_loss_pct=_safe_float(raw.get("avg_loss_pct"), 0.0),
                    expectancy=_safe_float(raw.get("expectancy"), 0.0),
                    sample_count=int(raw.get("sample_count", 0) or 0),
                    updated_at=str(raw.get("updated_at", "") or ""),
                )
        inst.last_rebalance_date = str(payload.get("last_rebalance_date", "") or "")
        return inst

    def update(self, strategy_id: str, pnl_pct: float) -> StrategyPerformance:
        sid = str(strategy_id or "unknown")
        perf = self.stats.get(sid, StrategyPerformance())
        value = _safe_float(pnl_pct, 0.0)
        perf.sample_count += 1
        if value > 0:
            perf.wins += 1
            prev = perf.avg_win_pct
            perf.avg_win_pct = prev + (value - prev) / max(1, perf.wins)
        elif value < 0:
            perf.losses += 1
            prev = perf.avg_loss_pct
            perf.avg_loss_pct = prev + (abs(value) - prev) / max(1, perf.losses)

        p = perf.wins / perf.sample_count if perf.sample_count > 0 else 0.0
        perf.expectancy = (p * perf.avg_win_pct) - ((1.0 - p) * perf.avg_loss_pct)
        perf.updated_at = datetime.datetime.now().isoformat()
        self.stats[sid] = perf
        return perf

    def rebalance_weights_daily(
        self,
        current_weights: Dict[str, float],
        weight_min: float = 0.5,
        weight_max: float = 1.5,
        ema_alpha: float = 0.2,
        now: Optional[datetime.date] = None,
    ) -> Tuple[bool, Dict[str, float]]:
        now = now or datetime.date.today()
        now_key = now.isoformat()
        if self.last_rebalance_date == now_key:
            return False, dict(current_weights or {})

        out = dict(current_weights or {})
        lo = max(0.0, float(weight_min or 0.0))
        hi = max(lo, float(weight_max or lo))
        alpha = _clamp(float(ema_alpha or 0.2), 0.01, 1.0)
        for sid, cur in list(out.items()):
            perf = self.stats.get(sid, StrategyPerformance())
            # Expectancy + hit-rate blend
            hit_rate = (perf.wins / perf.sample_count) if perf.sample_count > 0 else 0.5
            expectancy_scale = _clamp(1.0 + (perf.expectancy / 10.0), 0.6, 1.4)
            target = _clamp((0.7 + 0.6 * hit_rate) * expectancy_scale, lo, hi)
            out[sid] = float(cur) * (1.0 - alpha) + target * alpha
            out[sid] = _clamp(out[sid], lo, hi)

        self.last_rebalance_date = now_key
        return True, out

    @staticmethod
    def load(path: str):
        if not os.path.exists(path):
            return StrategyPerformanceTracker()
        try:
            with open(path, "r", encoding="utf-8") as fp:
                raw = json.load(fp)
            return StrategyPerformanceTracker.from_dict(raw if isinstance(raw, dict) else {})
        except Exception:
            return StrategyPerformanceTracker()

    def save(self, path: str) -> bool:
        try:
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(self.to_dict(), fp, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False


def evaluate_meta_signal(
    payload: MetaSignalInput,
    tracker: Optional[StrategyPerformanceTracker] = None,
) -> MetaSignalOutput:
    tracker = tracker or StrategyPerformanceTracker()
    perf = tracker.get(payload.strategy_id)

    engine_score = _clamp(payload.engine_score, 0.0, 100.0)
    technical_regime_score = _clamp(payload.technical_regime_score, 0.0, 100.0)
    market_regime_score = _clamp(payload.market_regime_score, 0.0, 100.0)
    expected_value = _safe_float(perf.expectancy, 0.0)
    expectancy_score = _clamp(50.0 + (expected_value * 5.0), 0.0, 100.0)

    meta_score = (
        (0.50 * engine_score)
        + (0.20 * expectancy_score)
        + (0.15 * technical_regime_score)
        + (0.15 * market_regime_score)
    )
    gate_pass = (expected_value > float(payload.min_expectancy)) and (meta_score >= float(payload.score_threshold))

    return MetaSignalOutput(
        strategy_id=str(payload.strategy_id or ""),
        meta_score=meta_score,
        expected_value=expected_value,
        gate_pass=bool(gate_pass),
        components={
            "engine_score": engine_score,
            "expectancy_score": expectancy_score,
            "technical_regime_score": technical_regime_score,
            "market_regime_score": market_regime_score,
        },
    )
