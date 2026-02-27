"""Position sizing engine with risk-budget and optional Kelly adjustment."""

from dataclasses import dataclass, field
from typing import Dict, Any


_DRAWDOWN_MULTIPLIER = {
    "normal": 1.0,
    "caution": 0.7,
    "defense": 0.4,
    "halt": 0.0,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _normalize_win_rate(win_rate: float) -> float:
    wr = float(win_rate or 0.0)
    if wr > 1.0:
        wr = wr / 100.0
    return _clamp(wr, 0.0, 1.0)


def _kelly_fraction(win_rate: float, avg_win_pct: float, avg_loss_pct: float) -> float:
    p = _normalize_win_rate(win_rate)
    avg_win = max(0.0, float(avg_win_pct or 0.0))
    avg_loss = abs(float(avg_loss_pct or 0.0))
    if avg_win <= 0 or avg_loss <= 0:
        return 0.0

    b = avg_win / avg_loss
    if b <= 0:
        return 0.0

    return p - ((1.0 - p) / b)


@dataclass
class PositionSizingInput:
    use_risk_budget_sizing: bool = False
    equity_krw: float = 0.0
    available_krw: float = 0.0
    current_price: float = 0.0
    atr_value: float = 0.0

    base_betting_pct: float = 10.0
    risk_budget_pct: float = 0.5
    atr_stop_mult: float = 2.0
    min_stop_pct: float = 0.3
    max_betting_pct: float = 15.0

    use_kelly_adjustment: bool = False
    kelly_scale: float = 0.25
    win_rate: float = 0.5
    avg_win_pct: float = 1.0
    avg_loss_pct: float = 1.0

    drawdown_state: str = "normal"


@dataclass
class PositionSizingOutput:
    position_ratio_pct: float
    order_notional_krw: float
    risk_per_trade_krw: float
    stop_distance_pct: float
    kelly_fraction_pct: float
    drawdown_multiplier: float
    details: Dict[str, Any] = field(default_factory=dict)


def _resolve_drawdown_multiplier(state: str) -> float:
    return float(_DRAWDOWN_MULTIPLIER.get(str(state or "normal").lower(), 1.0))


def _calc_stop_distance_pct(current_price: float, atr_value: float, atr_stop_mult: float, min_stop_pct: float) -> float:
    cur = float(current_price or 0.0)
    atr = max(0.0, float(atr_value or 0.0))
    atr_mult = max(0.0, float(atr_stop_mult or 0.0))
    min_stop = max(0.01, float(min_stop_pct or 0.0))
    if cur <= 0:
        return min_stop
    atr_stop_pct = (atr_mult * atr / cur) * 100.0
    return max(min_stop, atr_stop_pct)


def compute_position_size(inp: PositionSizingInput) -> PositionSizingOutput:
    available = max(0.0, float(inp.available_krw or 0.0))
    equity = max(0.0, float(inp.equity_krw or 0.0))
    base_ratio = _clamp(float(inp.base_betting_pct or 0.0), 0.0, 100.0)
    max_betting = _clamp(float(inp.max_betting_pct or 0.0), 0.0, 100.0)
    drawdown_mult = _resolve_drawdown_multiplier(inp.drawdown_state)

    details: Dict[str, Any] = {
        "use_risk_budget_sizing": bool(inp.use_risk_budget_sizing),
        "drawdown_state": str(inp.drawdown_state or "normal"),
    }

    risk_per_trade_krw = 0.0
    stop_distance_pct = _calc_stop_distance_pct(
        current_price=float(inp.current_price or 0.0),
        atr_value=float(inp.atr_value or 0.0),
        atr_stop_mult=float(inp.atr_stop_mult or 0.0),
        min_stop_pct=float(inp.min_stop_pct or 0.0),
    )

    kelly_raw = _kelly_fraction(inp.win_rate, inp.avg_win_pct, inp.avg_loss_pct)
    kelly_ratio_pct = 0.0
    if inp.use_kelly_adjustment:
        kelly_ratio_pct = _clamp(kelly_raw * float(inp.kelly_scale or 0.0) * 100.0, 0.0, max_betting or 100.0)

    if not inp.use_risk_budget_sizing:
        ratio = base_ratio
        if inp.use_kelly_adjustment and kelly_ratio_pct > 0:
            ratio = min(ratio, kelly_ratio_pct)
        ratio *= drawdown_mult
        ratio = _clamp(ratio, 0.0, 100.0)
        order_notional = available * (ratio / 100.0)
        details.update(
            {
                "mode": "legacy_base_ratio",
                "base_ratio_pct": base_ratio,
                "kelly_ratio_pct": kelly_ratio_pct,
            }
        )
        return PositionSizingOutput(
            position_ratio_pct=ratio,
            order_notional_krw=order_notional,
            risk_per_trade_krw=0.0,
            stop_distance_pct=stop_distance_pct,
            kelly_fraction_pct=kelly_ratio_pct,
            drawdown_multiplier=drawdown_mult,
            details=details,
        )

    risk_budget_pct = max(0.0, float(inp.risk_budget_pct or 0.0))
    risk_per_trade_krw = equity * (risk_budget_pct / 100.0)
    if stop_distance_pct <= 0:
        notional_by_risk = 0.0
    else:
        notional_by_risk = risk_per_trade_krw / (stop_distance_pct / 100.0)

    notional_cap_by_pct = available * (max_betting / 100.0)
    candidate_notional = min(notional_by_risk, notional_cap_by_pct)
    candidate_ratio = (candidate_notional / available * 100.0) if available > 0 else 0.0

    if inp.use_kelly_adjustment:
        candidate_ratio = min(candidate_ratio, kelly_ratio_pct)

    final_ratio = _clamp(candidate_ratio * drawdown_mult, 0.0, 100.0)
    final_notional = available * (final_ratio / 100.0)

    details.update(
        {
            "mode": "risk_budget",
            "risk_budget_pct": risk_budget_pct,
            "base_ratio_pct": base_ratio,
            "max_betting_pct": max_betting,
            "notional_by_risk": notional_by_risk,
            "notional_cap_by_pct": notional_cap_by_pct,
            "candidate_ratio_pct": candidate_ratio,
            "kelly_ratio_pct": kelly_ratio_pct,
            "kelly_raw": kelly_raw,
        }
    )

    return PositionSizingOutput(
        position_ratio_pct=final_ratio,
        order_notional_krw=final_notional,
        risk_per_trade_krw=risk_per_trade_krw,
        stop_distance_pct=stop_distance_pct,
        kelly_fraction_pct=kelly_ratio_pct,
        drawdown_multiplier=drawdown_mult,
        details=details,
    )

