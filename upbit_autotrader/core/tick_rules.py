"""Upbit KRW market tick size rules and rounding utilities."""

from __future__ import annotations

from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING, ROUND_HALF_UP


# Upbit KRW Market Tick Size Table
# (Lower bound inclusive, tick size)
KRW_TICK_RULES = [
    (2_000_000.0, 1_000.0),
    (1_000_000.0, 500.0),
    (500_000.0, 100.0),
    (100_000.0, 50.0),
    (10_000.0, 10.0),
    (1_000.0, 1.0),
    (100.0, 0.1),
    (10.0, 0.01),
    (1.0, 0.001),
    (0.0, 0.0001),
]


def get_tick_size(price: float, market: str = "KRW") -> float:
    """
    Get the minimum order price tick size for a given price in Upbit KRW market.
    """
    price_f = float(price or 0.0)
    if price_f <= 0.0:
        return 0.0001

    market_upper = str(market or "KRW").upper()
    if not market_upper.startswith("KRW"):
        # For BTC / USDT markets, default to 8 decimal places
        return 0.00000001

    for threshold, tick in KRW_TICK_RULES:
        if price_f >= threshold:
            return tick

    return 0.0001


def snap_to_tick_size(
    price: float,
    market: str = "KRW",
    method: str = "round",
) -> float:
    """
    Snap/align the given price to the valid Upbit tick size.
    method: 'round' (nearest), 'floor' (downward), 'ceil' (upward)
    """
    price_f = float(price or 0.0)
    if price_f <= 0.0:
        return 0.0

    tick = get_tick_size(price_f, market=market)
    d_price = Decimal(str(price_f))
    d_tick = Decimal(str(tick))

    method_lower = str(method or "round").lower()
    if method_lower == "floor":
        rounding_mode = ROUND_FLOOR
    elif method_lower == "ceil":
        rounding_mode = ROUND_CEILING
    else:
        rounding_mode = ROUND_HALF_UP

    snapped_steps = (d_price / d_tick).to_integral_value(rounding=rounding_mode)
    snapped_price = float(snapped_steps * d_tick)
    return max(0.0, snapped_price)
