"""
Holdings service for account-wide KRW market positions.
"""

from typing import List, Dict, Any

import pyupbit


def get_account_holdings(upbit, min_order_value: float = 5000.0) -> List[Dict[str, Any]]:
    """
    Read account balances and return KRW market holdings.
    Returned item keys:
      ticker, currency, qty, buy_price, current_price, value, pnl
    """
    balances = upbit.get_balances() or []

    tickers = []
    base_items = []
    for item in balances:
        currency = item.get("currency", "")
        if currency == "KRW":
            continue

        qty = float(item.get("balance", 0) or 0)
        if qty <= 0:
            continue

        avg_buy = float(item.get("avg_buy_price", 0) or 0)
        ticker = f"KRW-{currency}"
        tickers.append(ticker)
        base_items.append(
            {
                "ticker": ticker,
                "currency": currency,
                "qty": qty,
                "buy_price": avg_buy,
            }
        )

    prices_map = {}
    if tickers:
        try:
            prices = pyupbit.get_current_price(tickers)
            if isinstance(prices, dict):
                prices_map = prices
            elif len(tickers) == 1 and prices:
                prices_map = {tickers[0]: float(prices)}
        except Exception:
            prices_map = {}

    holdings = []
    for base in base_items:
        ticker = base["ticker"]
        qty = base["qty"]
        buy_price = base["buy_price"]
        current_price = float(prices_map.get(ticker, 0) or 0)

        value_basis = current_price if current_price > 0 else buy_price
        value = qty * value_basis
        if value < min_order_value:
            continue

        pnl = 0.0
        if buy_price > 0 and current_price > 0:
            pnl = (current_price - buy_price) / buy_price * 100

        holdings.append(
            {
                "ticker": ticker,
                "currency": base["currency"],
                "qty": qty,
                "buy_price": buy_price,
                "current_price": current_price,
                "value": value,
                "pnl": pnl,
            }
        )

    return holdings

