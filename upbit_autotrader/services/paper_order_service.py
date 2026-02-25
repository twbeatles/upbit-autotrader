"""Paper trading execution service for simulated fills."""

import datetime
from typing import Dict, Any, Optional, Tuple


class UpbitPaperOrderService:
    def __init__(self, fee_rate: float = 0.0005, slippage_bps: float = 5.0):
        self.fee_rate = float(fee_rate)
        self.slippage_bps = float(slippage_bps)
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._seq = 0
        self._krw_balance = 0.0
        self._holdings: Dict[str, Dict[str, float]] = {}

    def set_cost_model(self, fee_rate: Optional[float] = None, slippage_bps: Optional[float] = None):
        if fee_rate is not None:
            self.fee_rate = max(0.0, float(fee_rate))
        if slippage_bps is not None:
            self.slippage_bps = max(0.0, float(slippage_bps))

    def seed_balance(self, krw_balance: float):
        self._krw_balance = max(0.0, float(krw_balance or 0.0))

    def get_krw_balance(self) -> float:
        return float(self._krw_balance)

    def get_holdings(self) -> Dict[str, Dict[str, float]]:
        return {k: dict(v) for k, v in self._holdings.items() if float(v.get("qty", 0.0)) > 0}

    def get_order(self, uuid: str) -> Optional[Dict[str, Any]]:
        return self._orders.get(str(uuid))

    def _next_uuid(self, side: str) -> str:
        self._seq += 1
        return f"paper-{side.lower()}-{self._seq}"

    def _slipped_price(self, ref_price: float, side: str) -> float:
        if ref_price <= 0:
            return 0.0
        slip = (self.slippage_bps / 10000.0)
        if side.lower() in {"buy", "bid"}:
            return ref_price * (1.0 + slip)
        return ref_price * (1.0 - slip)

    def place_buy_market(
        self,
        ticker: str,
        krw_amount: float,
        market_price: float,
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        amount = float(krw_amount or 0.0)
        price = self._slipped_price(float(market_price or 0.0), "buy")
        if amount <= 0:
            return False, None, "매수 금액이 유효하지 않습니다."
        if price <= 0:
            return False, None, "시장 가격이 유효하지 않습니다."
        if amount > self._krw_balance:
            return False, None, "모의 잔고가 부족합니다."

        gross_amount = amount / (1.0 + self.fee_rate)
        qty = gross_amount / price
        if qty <= 0:
            return False, None, "체결 수량이 0입니다."

        fee = amount - gross_amount
        self._krw_balance -= amount

        holding = self._holdings.get(ticker, {"qty": 0.0, "avg_buy_price": 0.0})
        prev_qty = float(holding.get("qty", 0.0))
        prev_avg = float(holding.get("avg_buy_price", 0.0))
        new_qty = prev_qty + qty
        if new_qty > 0:
            new_avg = ((prev_qty * prev_avg) + (qty * price)) / new_qty
        else:
            new_avg = 0.0
        self._holdings[ticker] = {"qty": new_qty, "avg_buy_price": new_avg}

        uuid = self._next_uuid("BUY")
        order = {
            "uuid": uuid,
            "side": "bid",
            "ord_type": "price",
            "state": "done",
            "market": ticker,
            "created_at": datetime.datetime.now().isoformat(),
            "price": str(amount),
            "executed_volume": str(qty),
            "executed_funds": str(gross_amount),
            "paid_fee": str(fee),
            "trades": [{"price": str(price), "volume": str(qty)}],
        }
        self._orders[uuid] = order
        return True, {"uuid": uuid}, ""

    def place_sell_market(
        self,
        ticker: str,
        qty: float,
        market_price: float,
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        sell_qty = float(qty or 0.0)
        price = self._slipped_price(float(market_price or 0.0), "sell")
        if sell_qty <= 0:
            return False, None, "매도 수량이 유효하지 않습니다."
        if price <= 0:
            return False, None, "시장 가격이 유효하지 않습니다."

        holding = self._holdings.get(ticker, {"qty": 0.0, "avg_buy_price": 0.0})
        held_qty = float(holding.get("qty", 0.0))
        if held_qty + 1e-12 < sell_qty:
            return False, None, "모의 보유 수량이 부족합니다."

        gross = sell_qty * price
        fee = gross * self.fee_rate
        net = gross - fee
        self._krw_balance += net

        remain = max(0.0, held_qty - sell_qty)
        if remain > 0:
            self._holdings[ticker] = {"qty": remain, "avg_buy_price": float(holding.get("avg_buy_price", 0.0))}
        else:
            self._holdings.pop(ticker, None)

        uuid = self._next_uuid("SELL")
        order = {
            "uuid": uuid,
            "side": "ask",
            "ord_type": "market",
            "state": "done",
            "market": ticker,
            "created_at": datetime.datetime.now().isoformat(),
            "executed_volume": str(sell_qty),
            "executed_funds": str(gross),
            "paid_fee": str(fee),
            "trades": [{"price": str(price), "volume": str(sell_qty)}],
        }
        self._orders[uuid] = order
        return True, {"uuid": uuid}, ""
