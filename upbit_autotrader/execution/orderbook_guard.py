"""
Orderbook spread and depth analysis for pre-trade slippage guarding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class OrderbookAnalysisResult:
    market: str
    best_bid: float
    best_ask: float
    mid_price: float
    spread_bps: float
    top5_bid_krw: float
    top5_ask_krw: float
    estimated_fill_price: float
    estimated_slippage_bps: float
    is_safe: bool
    reason: str = ""
    recommended_slices: int = 1


def analyze_orderbook_depth(
    orderbook: Dict[str, Any],
    notional_krw: float = 0.0,
    side: str = "BUY",
    max_spread_bps: float = 40.0,
    max_slippage_bps: float = 30.0,
) -> OrderbookAnalysisResult:
    """
    Analyze orderbook spread and available liquidity depth.
    Estimates execution price and slippage before submitting large market orders.
    """
    market = str(orderbook.get("market") or "")
    units = list(orderbook.get("orderbook_units") or [])
    if not units:
        return OrderbookAnalysisResult(
            market=market,
            best_bid=0.0,
            best_ask=0.0,
            mid_price=0.0,
            spread_bps=9999.0,
            top5_bid_krw=0.0,
            top5_ask_krw=0.0,
            estimated_fill_price=0.0,
            estimated_slippage_bps=9999.0,
            is_safe=False,
            reason="호가 데이터 없음",
        )

    best_ask = float(units[0].get("ask_price", 0.0) or 0.0)
    best_bid = float(units[0].get("bid_price", 0.0) or 0.0)
    if best_ask <= 0 or best_bid <= 0:
        return OrderbookAnalysisResult(
            market=market,
            best_bid=best_bid,
            best_ask=best_ask,
            mid_price=0.0,
            spread_bps=9999.0,
            top5_bid_krw=0.0,
            top5_ask_krw=0.0,
            estimated_fill_price=0.0,
            estimated_slippage_bps=9999.0,
            is_safe=False,
            reason="비정상 호가 가격",
        )

    mid_price = (best_ask + best_bid) / 2.0
    spread_bps = ((best_ask - best_bid) / mid_price) * 10000.0 if mid_price > 0 else 9999.0

    top5_bid_krw = 0.0
    top5_ask_krw = 0.0
    for u in units[:5]:
        bp = float(u.get("bid_price", 0.0) or 0.0)
        bs = float(u.get("bid_size", 0.0) or 0.0)
        ap = float(u.get("ask_price", 0.0) or 0.0)
        asize = float(u.get("ask_size", 0.0) or 0.0)
        top5_bid_krw += bp * bs
        top5_ask_krw += ap * asize

    side_upper = str(side or "BUY").upper()
    req_notional = float(notional_krw or 0.0)
    if req_notional <= 0:
        # No fill estimation requested, just assess spread
        is_safe = spread_bps <= max_spread_bps
        reason = "" if is_safe else f"스프레드 과다 ({spread_bps:.1f} bps > {max_spread_bps:.1f} bps)"
        return OrderbookAnalysisResult(
            market=market,
            best_bid=best_bid,
            best_ask=best_ask,
            mid_price=mid_price,
            spread_bps=spread_bps,
            top5_bid_krw=top5_bid_krw,
            top5_ask_krw=top5_ask_krw,
            estimated_fill_price=best_ask if side_upper == "BUY" else best_bid,
            estimated_slippage_bps=0.0,
            is_safe=is_safe,
            reason=reason,
            recommended_slices=1,
        )

    # Estimate fill price by consuming orderbook levels
    remaining_krw = req_notional
    total_qty = 0.0
    total_spend = 0.0

    if side_upper == "BUY":
        reference_price = best_ask
        for u in units:
            level_price = float(u.get("ask_price", 0.0) or 0.0)
            level_size = float(u.get("ask_size", 0.0) or 0.0)
            if level_price <= 0 or level_size <= 0:
                continue
            level_max_krw = level_price * level_size
            if remaining_krw <= level_max_krw:
                qty_here = remaining_krw / level_price
                total_qty += qty_here
                total_spend += remaining_krw
                remaining_krw = 0.0
                break
            else:
                total_qty += level_size
                total_spend += level_max_krw
                remaining_krw -= level_max_krw
    else:
        reference_price = best_bid
        for u in units:
            level_price = float(u.get("bid_price", 0.0) or 0.0)
            level_size = float(u.get("bid_size", 0.0) or 0.0)
            if level_price <= 0 or level_size <= 0:
                continue
            level_max_krw = level_price * level_size
            if remaining_krw <= level_max_krw:
                qty_here = remaining_krw / level_price
                total_qty += qty_here
                total_spend += remaining_krw
                remaining_krw = 0.0
                break
            else:
                total_qty += level_size
                total_spend += level_max_krw
                remaining_krw -= level_max_krw

    if remaining_krw > 0:
        # Exhausted all orderbook levels
        avg_fill_price = (total_spend / total_qty) if total_qty > 0 else reference_price * 1.05
        slippage_bps = 9999.0
        return OrderbookAnalysisResult(
            market=market,
            best_bid=best_bid,
            best_ask=best_ask,
            mid_price=mid_price,
            spread_bps=spread_bps,
            top5_bid_krw=top5_bid_krw,
            top5_ask_krw=top5_ask_krw,
            estimated_fill_price=avg_fill_price,
            estimated_slippage_bps=slippage_bps,
            is_safe=False,
            reason=f"호가 깊이 부족 (미소진 잔여: {remaining_krw:,.0f}원)",
            recommended_slices=max(3, int(req_notional / max(1.0, top5_ask_krw / 2.0)) + 1),
        )

    avg_fill_price = (total_spend / total_qty) if total_qty > 0 else reference_price
    if side_upper == "BUY":
        slippage_bps = max(0.0, (avg_fill_price - reference_price) / reference_price * 10000.0)
    else:
        slippage_bps = max(0.0, (reference_price - avg_fill_price) / reference_price * 10000.0)

    is_safe = (spread_bps <= max_spread_bps) and (slippage_bps <= max_slippage_bps)
    reason = ""
    if not is_safe:
        if spread_bps > max_spread_bps:
            reason = f"스프레드 과다 ({spread_bps:.1f} bps > {max_spread_bps:.1f} bps)"
        else:
            reason = f"예상 슬리피지 과다 ({slippage_bps:.1f} bps > {max_slippage_bps:.1f} bps)"

    recommended_slices = 1
    if slippage_bps > max_slippage_bps:
        recommended_slices = max(2, min(8, int(slippage_bps / max_slippage_bps * 2)))

    return OrderbookAnalysisResult(
        market=market,
        best_bid=best_bid,
        best_ask=best_ask,
        mid_price=mid_price,
        spread_bps=spread_bps,
        top5_bid_krw=top5_bid_krw,
        top5_ask_krw=top5_ask_krw,
        estimated_fill_price=avg_fill_price,
        estimated_slippage_bps=slippage_bps,
        is_safe=is_safe,
        reason=reason,
        recommended_slices=recommended_slices,
    )
