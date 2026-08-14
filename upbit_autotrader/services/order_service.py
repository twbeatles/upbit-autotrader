"""
Order service for duplicate-order prevention and pending state tracking.
"""

import datetime
from typing import Dict, Any, Tuple, Optional, Iterable


class UpbitOrderService:
    STATE_SUBMITTED = "submitted"
    STATE_WAIT = "wait"
    STATE_DONE = "done"
    STATE_CANCEL = "cancel"
    STATE_TIMEOUT = "timeout"
    STATE_MANUAL_REVIEW = "manual_review"
    STATE_RECONCILED = "reconciled"

    _ALLOWED_TRANSITIONS = {
        STATE_SUBMITTED: {STATE_WAIT, STATE_DONE, STATE_CANCEL, STATE_TIMEOUT},
        STATE_WAIT: {STATE_DONE, STATE_CANCEL, STATE_TIMEOUT},
        STATE_TIMEOUT: {STATE_WAIT, STATE_DONE, STATE_CANCEL, STATE_MANUAL_REVIEW},
        STATE_MANUAL_REVIEW: {STATE_RECONCILED, STATE_DONE, STATE_CANCEL},
        STATE_RECONCILED: set(),
        STATE_DONE: set(),
        STATE_CANCEL: set(),
    }

    def __init__(self):
        self.pending_orders: Dict[str, Dict[str, Any]] = {}

    def get_pending(self, ticker: str) -> Optional[Dict[str, Any]]:
        return self.pending_orders.get(ticker)

    def has_pending(self, ticker: str) -> bool:
        return ticker in self.pending_orders

    def mark_pending(
        self,
        ticker: str,
        side: str,
        uuid: str,
        session_id: int = 0,
        source: str = "",
        reserved_krw: float = 0.0,
        retry_count: int = 0,
        identifier: str = "",
    ) -> None:
        now = datetime.datetime.now()
        lifecycle_state = self.STATE_SUBMITTED
        self.pending_orders[ticker] = {
            "side": side,
            "uuid": uuid,
            "identifier": str(identifier or ""),
            "requested_at": now,
            "session_id": int(session_id or 0),
            "source": source or "",
            "reserved_krw": float(reserved_krw or 0.0),
            "last_checked_at": now,
            "retry_count": int(retry_count or 0),
            "lifecycle_state": lifecycle_state,
            "lifecycle_history": [
                {
                    "state": lifecycle_state,
                    "at": now.isoformat(),
                    "reason": "mark_pending",
                }
            ],
            "needs_manual_review": False,
        }

    def clear_pending(self, ticker: str) -> None:
        self.pending_orders.pop(ticker, None)

    def clear_pending_if_uuid(self, ticker: str, uuid: str) -> bool:
        pending = self.pending_orders.get(ticker)
        if not pending:
            return False
        if str(pending.get("uuid")) != str(uuid):
            return False
        self.pending_orders.pop(ticker, None)
        return True

    def clear_pending_if_identifier(self, ticker: str, identifier: str) -> bool:
        pending = self.pending_orders.get(ticker)
        if not pending:
            return False
        if str(pending.get("identifier")) != str(identifier):
            return False
        self.pending_orders.pop(ticker, None)
        return True

    def update_pending(self, ticker: str, **fields: Any) -> Optional[Dict[str, Any]]:
        pending = self.pending_orders.get(ticker)
        if not pending:
            return None
        pending.update(fields)
        self._ensure_lifecycle_fields(pending)
        return pending

    def list_pending(self) -> Dict[str, Dict[str, Any]]:
        return dict(self.pending_orders)

    def get_pending_by_uuid(self, uuid: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        for ticker, pending in self.pending_orders.items():
            if str(pending.get("uuid")) == str(uuid):
                return ticker, pending
        return None, None

    def get_pending_by_identifier(self, identifier: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        if not identifier:
            return None, None
        for ticker, pending in self.pending_orders.items():
            if str(pending.get("identifier")) == str(identifier):
                return ticker, pending
        return None, None

    def transition_pending(
        self,
        ticker: str,
        next_state: str,
        reason: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime.datetime] = None,
    ) -> bool:
        pending = self.pending_orders.get(ticker)
        if not pending:
            return False

        self._ensure_lifecycle_fields(pending)
        current_state = str(pending.get("lifecycle_state", self.STATE_SUBMITTED) or self.STATE_SUBMITTED)
        next_state = str(next_state or "").strip().lower()
        if not next_state:
            return False
        if current_state == next_state:
            return True

        allowed_next = self._ALLOWED_TRANSITIONS.get(current_state, set())
        if next_state not in allowed_next:
            return False

        now = timestamp or datetime.datetime.now()
        pending["lifecycle_state"] = next_state
        if next_state == self.STATE_MANUAL_REVIEW:
            pending["needs_manual_review"] = True
        history = pending.get("lifecycle_history")
        if not isinstance(history, list):
            history = []
            pending["lifecycle_history"] = history
        history.append(
            {
                "state": next_state,
                "at": now.isoformat(),
                "reason": reason or "",
                "metadata": metadata or {},
            }
        )
        return True

    def _ensure_lifecycle_fields(self, pending: Dict[str, Any]) -> None:
        if "lifecycle_state" not in pending:
            pending["lifecycle_state"] = self.STATE_SUBMITTED
        if "lifecycle_history" not in pending or not isinstance(pending.get("lifecycle_history"), list):
            pending["lifecycle_history"] = []
        if "needs_manual_review" not in pending:
            pending["needs_manual_review"] = False

    def place_buy_market(
        self,
        upbit,
        ticker: str,
        krw_amount: float,
        pending_meta: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        pending = self.get_pending(ticker)
        if pending:
            return False, None, f"이미 {pending['side']} 주문이 대기 중입니다."

        result = upbit.buy_market_order(ticker, krw_amount)
        if result and "uuid" in result:
            meta = pending_meta or {}
            self.mark_pending(
                ticker,
                "BUY",
                result["uuid"],
                session_id=meta.get("session_id", 0),
                source=meta.get("source", ""),
                reserved_krw=meta.get("reserved_krw", 0.0),
                retry_count=meta.get("retry_count", 0),
            )
            return True, result, ""
        return False, result, "매수 주문 응답이 비정상입니다."

    def place_sell_market(
        self,
        upbit,
        ticker: str,
        qty: float,
        side: str = "SELL",
        pending_meta: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        pending = self.get_pending(ticker)
        if pending:
            return False, None, f"이미 {pending['side']} 주문이 대기 중입니다."

        result = upbit.sell_market_order(ticker, qty)
        if result and "uuid" in result:
            meta = pending_meta or {}
            self.mark_pending(
                ticker,
                side,
                result["uuid"],
                session_id=meta.get("session_id", 0),
                source=meta.get("source", ""),
                reserved_krw=meta.get("reserved_krw", 0.0),
                retry_count=meta.get("retry_count", 0),
            )
            return True, result, ""
        return False, result, "매도 주문 응답이 비정상입니다."

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _sum_trade_funds(cls, trades: Optional[Iterable[Dict[str, Any]]]) -> float:
        if not trades:
            return 0.0

        total = 0.0
        for trade in trades:
            price = cls._safe_float(trade.get("price"))
            volume = cls._safe_float(trade.get("volume"))
            if price > 0 and volume > 0:
                total += price * volume
        return total

    @classmethod
    def get_executed_funds(cls, order: Optional[Dict[str, Any]]) -> float:
        """
        Return gross executed KRW value of an order.
        Priority: trades sum -> executed_funds -> price fallback.
        """
        if not order:
            return 0.0

        funds = cls._sum_trade_funds(order.get("trades"))
        if funds > 0:
            return funds

        executed_funds = cls._safe_float(order.get("executed_funds"))
        if executed_funds > 0:
            return executed_funds

        executed_volume = cls._safe_float(order.get("executed_volume"))
        price = cls._safe_float(order.get("price"))
        if executed_volume <= 0 or price <= 0:
            return 0.0

        ord_type = str(order.get("ord_type", "")).lower()
        side = str(order.get("side", "")).lower()
        # price is unit-price for limit orders, but market bid commonly stores KRW spend.
        if ord_type == "limit":
            return price * executed_volume
        if side == "bid":
            return price
        return price * executed_volume

    @classmethod
    def get_buy_fill_metrics(cls, order: Optional[Dict[str, Any]]) -> Tuple[float, float, float]:
        """
        Return (executed_volume, total_cost_including_fee, average_cost_price).
        """
        executed_volume = cls._safe_float(order.get("executed_volume") if order else 0.0)
        if executed_volume <= 0:
            return 0.0, 0.0, 0.0

        gross_funds = cls.get_executed_funds(order)
        paid_fee = cls._safe_float(order.get("paid_fee") if order else 0.0)
        total_cost = max(0.0, gross_funds + paid_fee)
        avg_price = (total_cost / executed_volume) if total_cost > 0 else 0.0
        return executed_volume, total_cost, avg_price

    @classmethod
    def get_sell_fill_metrics(cls, order: Optional[Dict[str, Any]]) -> Tuple[float, float, float]:
        """
        Return (executed_volume, net_proceeds_after_fee, average_net_sell_price).
        """
        executed_volume = cls._safe_float(order.get("executed_volume") if order else 0.0)
        if executed_volume <= 0:
            return 0.0, 0.0, 0.0

        gross_funds = cls.get_executed_funds(order)
        paid_fee = cls._safe_float(order.get("paid_fee") if order else 0.0)
        net_proceeds = max(0.0, gross_funds - paid_fee)
        avg_net_price = (net_proceeds / executed_volume) if net_proceeds > 0 else 0.0
        return executed_volume, net_proceeds, avg_net_price

    @staticmethod
    def apply_partial_sell_accounting(invest_amt: float, remaining_qty: float, executed_volume: float, executed_price: float) -> Tuple[float, float]:
        """
        Return (new_invest_amt, realized_profit) after partial sell fill.
        remaining_qty should already reflect the post-fill quantity.
        """
        total_qty_before_sell = remaining_qty + executed_volume
        buy_portion = 0.0
        if total_qty_before_sell > 0:
            buy_portion = invest_amt * (executed_volume / total_qty_before_sell)

        sell_amount = executed_volume * executed_price
        realized_profit = sell_amount - buy_portion
        new_invest_amt = max(0.0, invest_amt - buy_portion)
        return new_invest_amt, realized_profit
