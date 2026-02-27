"""Execution planning helpers for slippage-aware market and TWAP routing."""

from dataclasses import dataclass, field
from typing import List


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


@dataclass
class ExecutionConfig:
    enabled: bool = False
    expected_slippage_guard_bps: float = 30.0
    twap_slices: int = 3
    twap_interval_sec: int = 8
    fee_bps: float = 5.0
    default_mode: str = "single_market"
    min_order_krw: float = 5000.0


@dataclass
class ExecutionPlan:
    mode: str
    order_notional_krw: float
    slice_notionals: List[float] = field(default_factory=list)
    expected_slippage_bps: float = 0.0
    breakeven_pct: float = 0.0
    blocked: bool = False
    reason: str = ""


def estimate_expected_slippage_bps(
    realized_vol_pct: float,
    order_notional_krw: float,
    est_liquidity_krw: float = 50_000_000.0,
    base_slippage_bps: float = 5.0,
) -> float:
    vol = max(0.0, float(realized_vol_pct or 0.0))
    notional = max(0.0, float(order_notional_krw or 0.0))
    liquidity = max(1.0, float(est_liquidity_krw or 0.0))
    size_ratio = _clamp(notional / liquidity, 0.0, 1.0)

    slippage = float(base_slippage_bps) + (vol * 0.6) + (size_ratio * 40.0)
    return _clamp(slippage, 0.0, 500.0)


def compute_breakeven_pct(
    fee_buy_bps: float,
    fee_sell_bps: float,
    expected_slippage_buy_bps: float,
    expected_slippage_sell_bps: float,
) -> float:
    # Return in percent unit, e.g. 0.20 means 0.20%.
    total_bps = (
        max(0.0, float(fee_buy_bps or 0.0))
        + max(0.0, float(fee_sell_bps or 0.0))
        + max(0.0, float(expected_slippage_buy_bps or 0.0))
        + max(0.0, float(expected_slippage_sell_bps or 0.0))
    )
    return total_bps / 100.0


def build_twap_schedule(total_notional_krw: float, slices: int, min_order_krw: float = 5000.0) -> List[float]:
    total = max(0.0, float(total_notional_krw or 0.0))
    min_order = max(0.0, float(min_order_krw or 0.0))
    n = max(1, int(slices or 1))
    if total <= 0:
        return []
    if n <= 1:
        return [total]

    base = total / n
    if min_order > 0 and base < min_order:
        n = int(total // min_order)
        if n < 2:
            return [total]
        base = total / n

    schedule = [base] * n
    # Preserve exact notional sum and avoid negative drift.
    schedule[-1] = total - sum(schedule[:-1])
    return [max(0.0, float(v)) for v in schedule if v > 0]


def plan_execution(
    config: ExecutionConfig,
    order_notional_krw: float,
    *,
    realized_vol_pct: float = 0.0,
    est_liquidity_krw: float = 50_000_000.0,
    force_mode: str = "",
) -> ExecutionPlan:
    target_notional = max(0.0, float(order_notional_krw or 0.0))
    if target_notional <= 0:
        return ExecutionPlan(
            mode="single_market",
            order_notional_krw=0.0,
            slice_notionals=[],
            blocked=True,
            reason="order_notional_non_positive",
        )

    if not config.enabled:
        return ExecutionPlan(
            mode="single_market",
            order_notional_krw=target_notional,
            slice_notionals=[target_notional],
            expected_slippage_bps=0.0,
            breakeven_pct=compute_breakeven_pct(config.fee_bps, config.fee_bps, 0.0, 0.0),
        )

    expected_slippage = estimate_expected_slippage_bps(
        realized_vol_pct=realized_vol_pct,
        order_notional_krw=target_notional,
        est_liquidity_krw=est_liquidity_krw,
        base_slippage_bps=config.fee_bps,
    )
    adjusted_notional = target_notional
    blocked = False
    reason = ""
    guard = max(0.0, float(config.expected_slippage_guard_bps or 0.0))
    if guard > 0 and expected_slippage > guard:
        scale = _clamp(guard / expected_slippage, 0.2, 1.0)
        adjusted_notional *= scale
        reason = "slippage_guard_scaled"
        if adjusted_notional < config.min_order_krw:
            blocked = True
            reason = "slippage_guard_blocked"

    mode = str(force_mode or config.default_mode or "single_market")
    if mode not in {"single_market", "twap_market"}:
        mode = "single_market"
    if mode == "twap_market" and int(config.twap_slices) < 2:
        mode = "single_market"

    if blocked:
        return ExecutionPlan(
            mode=mode,
            order_notional_krw=adjusted_notional,
            slice_notionals=[],
            expected_slippage_bps=expected_slippage,
            breakeven_pct=compute_breakeven_pct(config.fee_bps, config.fee_bps, expected_slippage, expected_slippage),
            blocked=True,
            reason=reason,
        )

    if mode == "twap_market":
        slices = build_twap_schedule(adjusted_notional, int(config.twap_slices), config.min_order_krw)
        if len(slices) <= 1:
            mode = "single_market"
            slices = [adjusted_notional]
    else:
        slices = [adjusted_notional]

    return ExecutionPlan(
        mode=mode,
        order_notional_krw=adjusted_notional,
        slice_notionals=slices,
        expected_slippage_bps=expected_slippage,
        breakeven_pct=compute_breakeven_pct(config.fee_bps, config.fee_bps, expected_slippage, expected_slippage),
        blocked=False,
        reason=reason,
    )


def estimate_realized_slippage_bps(reference_price: float, executed_avg_price: float, side: str = "buy") -> float:
    ref = float(reference_price or 0.0)
    exe = float(executed_avg_price or 0.0)
    if ref <= 0 or exe <= 0:
        return 0.0

    side_l = str(side or "buy").lower()
    if side_l in {"sell", "ask"}:
        # For sell, lower execution price than reference is negative quality.
        return (ref - exe) / ref * 10000.0
    return (exe - ref) / ref * 10000.0

