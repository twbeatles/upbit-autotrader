from __future__ import annotations

from typing import Any, cast

from PyQt6.QtWidgets import QTableWidgetItem

from upbit_autotrader.core.config import Config


def get_balance(self):
    """잔고 조회"""
    if self._is_paper_mode():
        svc = self._ensure_paper_service_state()
        if svc is None:
            return
        self.balance = float(svc.get_krw_balance())
        self.lbl_balance.setText(f"💰 주문가능금액: {self.balance:,.0f} 원 [PAPER]")
        return

    if not self.upbit:
        return
    try:
        balance = self._api_get_balance("KRW")
        if balance is None:
            self.logger.warning("잔고 조회 결과가 None입니다.")
            return
        self.balance = float(balance)
        self.lbl_balance.setText(f"💰 주문가능금액: {self.balance:,.0f} 원")
    except Exception as e:
        self.logger.error(f"잔고 조회 실패: {e}")


def _get_reserved_krw_total(self):
    self._ensure_order_stability_state()
    return sum(max(0.0, float(v or 0.0)) for v in self._reserved_krw_by_ticker.values())


def _get_available_krw(self):
    balance = float(getattr(self, "balance", 0) or 0)
    return max(0.0, balance - _get_reserved_krw_total(self))


def _calculate_current_equity(self, account_wide_positions=None):
    cash_krw = float(getattr(self, "balance", 0.0) or 0.0)
    reserved_krw = _get_reserved_krw_total(self)
    positions = account_wide_positions
    if positions is None:
        positions = {}
        for ticker, info in getattr(self, "universe", {}).items():
            qty = float(info.get("qty", 0.0) or 0.0)
            if qty <= 0:
                continue
            cur = float(info.get("current", 0.0) or 0.0)
            buy = float(info.get("buy_price", 0.0) or 0.0)
            positions[ticker] = {"qty": qty, "current_price": cur, "buy_price": buy}
    gross_exposure = 0.0
    unrealized_pnl = 0.0
    for pos in dict(positions or {}).values():
        qty = float(pos.get("qty", 0.0) or 0.0)
        buy_price = float(pos.get("buy_price", 0.0) or 0.0)
        current_price = float(pos.get("current_price", 0.0) or pos.get("current", 0.0) or 0.0)
        if qty <= 0:
            continue
        basis = current_price if current_price > 0 else buy_price
        gross_exposure += max(0.0, qty * basis)
        if buy_price > 0 and current_price > 0:
            unrealized_pnl += (current_price - buy_price) * qty
    equity = max(0.0, cash_krw + reserved_krw + gross_exposure)
    return {
        "equity_krw": equity,
        "cash_krw": cash_krw,
        "reserved_krw": reserved_krw,
        "gross_exposure_krw": gross_exposure,
        "unrealized_pnl": unrealized_pnl,
    }


def _reserve_krw_for_buy(self, ticker, amount, session_id=0):
    self._ensure_order_stability_state()
    amount = float(amount or 0.0)
    if amount <= 0:
        return False
    existing = float(self._reserved_krw_by_ticker.get(ticker, 0.0) or 0.0)
    available = _get_available_krw(self) + existing
    if amount > (available + 1e-8):
        return False
    self._reserved_krw_by_ticker[ticker] = amount
    self._mark_reconciliation_dirty()
    return True


def _release_reserved_krw(self, ticker):
    self._ensure_order_stability_state()
    released = float(self._reserved_krw_by_ticker.pop(ticker, 0.0) or 0.0)
    if released > 0:
        self._mark_reconciliation_dirty()
    return released


def _sync_reserved_with_pending(self):
    self._ensure_order_stability_state()
    if not hasattr(self, "order_service"):
        self._reserved_krw_by_ticker.clear()
        return
    if hasattr(self.order_service, "list_pending"):
        pending_tickers = set(self.order_service.list_pending().keys())
    else:
        pending_tickers = set(getattr(self, "pending_orders", {}).keys())
    for ticker in list(self._reserved_krw_by_ticker.keys()):
        if ticker not in pending_tickers:
            self._reserved_krw_by_ticker.pop(ticker, None)
    self._mark_reconciliation_dirty()


def _fetch_account_holdings(self):
    if hasattr(self, "get_account_holdings"):
        try:
            return list(self.get_account_holdings() or [])
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.warning(f"계좌 보유 조회 실패: {e}")
    return []


def _build_holdings_map(self, account_holdings=None):
    holdings = list(account_holdings or [])
    holdings_map = {}
    for item in holdings:
        ticker = str(item.get("ticker") or "").strip()
        if not ticker:
            continue
        qty = float(item.get("qty", 0.0) or 0.0)
        buy_price = float(item.get("buy_price", 0.0) or 0.0)
        current_price = float(item.get("current_price", 0.0) or 0.0)
        if current_price <= 0:
            current_price = float(item.get("current", 0.0) or 0.0)
        value = float(item.get("value", qty * current_price) or 0.0)
        holdings_map[ticker] = {
            "ticker": ticker,
            "qty": qty,
            "buy_price": buy_price,
            "current_price": current_price,
            "value": value,
        }
    return holdings_map


def _ensure_universe_row(self, ticker):
    info = self.universe.get(ticker)
    if info is None:
        row = len(self.universe)
        info = {
            "name": ticker,
            "state": "감시중",
            "row": row,
            "target": 0.0,
            "ma5": 0.0,
            "current": 0.0,
            "qty": 0.0,
            "buy_price": 0.0,
            "invest_amt": 0.0,
            "high_since_buy": 0.0,
            "max_profit_rate": 0.0,
            "partial_sold": [],
        }
        self.universe[ticker] = info
        if hasattr(self, "table"):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(ticker))
            self.table.setItem(row, 1, QTableWidgetItem("-"))
            self.table.setItem(row, 2, QTableWidgetItem("-"))
            self.table.setItem(row, 3, QTableWidgetItem("-"))
            self.set_table_item(row, 4, "👀 감시중", "#00b894")
            self.table.setItem(row, 5, QTableWidgetItem("0.00000000"))
            self.table.setItem(row, 6, QTableWidgetItem("-"))
            self.table.setItem(row, 7, QTableWidgetItem("-"))
            self.table.setItem(row, 8, QTableWidgetItem("-"))
            self.table.setItem(row, 9, QTableWidgetItem("-"))
            info["ui_items"] = {
                "price": self.table.item(row, 1),
                "state": self.table.item(row, 4),
                "qty": self.table.item(row, 5),
                "buy_price": self.table.item(row, 6),
                "profit": self.table.item(row, 7),
                "max_profit": self.table.item(row, 8),
                "invest": self.table.item(row, 9),
            }
    return info


def _sync_account_holdings_to_universe(self, account_holdings=None, include_external=None):
    if not hasattr(self, "universe"):
        return
    include_external = self._enable_account_wide_sync() if include_external is None else bool(include_external)
    holdings_map = _build_holdings_map(self, account_holdings or _fetch_account_holdings(self))
    for ticker, holding in holdings_map.items():
        if not include_external and ticker not in self.universe:
            continue
        info = _ensure_universe_row(self, ticker)
        qty = float(holding.get("qty", 0.0) or 0.0)
        buy_price = float(holding.get("buy_price", 0.0) or 0.0)
        current = float(holding.get("current_price", 0.0) or info.get("current", 0.0) or 0.0)
        info["qty"] = qty
        info["buy_price"] = buy_price
        info["current"] = current
        info["invest_amt"] = max(0.0, qty * buy_price)
        if qty > 0:
            info["state"] = "보유중"
            info["high_since_buy"] = max(current, buy_price)
            info.setdefault("partial_sold", [])
            self.set_table_item(info["row"], 4, "💼 보유중", "#00b4d8")
        else:
            info["state"] = "감시중"
            self.set_table_item(info["row"], 4, "👀 감시중", "#00b894")
        ui_items = info.get("ui_items", {})
        qty_item = ui_items.get("qty")
        if qty_item is None and hasattr(self, "table"):
            qty_item = QTableWidgetItem("0.00000000")
            self.table.setItem(info["row"], 5, qty_item)
            info.setdefault("ui_items", {})["qty"] = qty_item
        if qty_item is not None:
            qty_item.setText(f"{qty:.8f}" if qty > 0 else "0.00000000")
        buy_price_item = ui_items.get("buy_price")
        if buy_price_item is None and hasattr(self, "table"):
            buy_price_item = QTableWidgetItem("-")
            self.table.setItem(info["row"], 6, buy_price_item)
            info.setdefault("ui_items", {})["buy_price"] = buy_price_item
        if buy_price_item is not None:
            buy_price_item.setText(f"{buy_price:,.0f}" if buy_price > 0 else "-")
        invest_item = ui_items.get("invest")
        if invest_item is None and hasattr(self, "table"):
            invest_item = QTableWidgetItem("-")
            self.table.setItem(info["row"], 9, invest_item)
            info.setdefault("ui_items", {})["invest"] = invest_item
        if invest_item is not None:
            invest_item.setText(f"{info['invest_amt']:,.0f}" if info["invest_amt"] > 0 else "-")

    if include_external:
        held_tickers = {t for t, h in holdings_map.items() if float(h.get("qty", 0.0) or 0.0) > 0}
        for ticker, info in self.universe.items():
            if ticker in held_tickers:
                continue
            if float(info.get("qty", 0.0) or 0.0) <= 0:
                continue
            if self.order_service.has_pending(ticker):
                continue
            info["qty"] = 0.0
            info["buy_price"] = 0.0
            info["invest_amt"] = 0.0
            info["high_since_buy"] = 0.0
            info["max_profit_rate"] = 0.0
            info["partial_sold"] = []
            info["state"] = "감시중"
            self.set_table_item(info["row"], 4, "👀 감시중", "#00b894")
    self._risk_snapshot_cache = {"ts": 0.0, "value": None}


def _is_paper_mode(self):
    return bool(hasattr(self, "chk_paper_trading") and self.chk_paper_trading.isChecked())


def _allow_paper_without_login(self):
    if hasattr(self, "chk_paper_allow_without_login"):
        return bool(self.chk_paper_allow_without_login.isChecked())
    return bool(getattr(Config, "DEFAULT_PAPER_ALLOW_WITHOUT_LOGIN", True))


def _get_paper_seed_krw(self):
    if hasattr(self, "spin_paper_seed_krw"):
        return max(0.0, float(self.spin_paper_seed_krw.value() or 0.0))
    return float(getattr(Config, "DEFAULT_PAPER_SEED_KRW", 10_000_000) or 0.0)


def _ensure_paper_service_state(self):
    svc = getattr(self, "paper_order_service", None)
    if svc is None:
        return None
    fee_bps = self.spin_paper_fee_bps.value() if hasattr(self, "spin_paper_fee_bps") else Config.DEFAULT_PAPER_FEE_BPS
    slip_bps = (
        self.spin_paper_slippage_bps.value()
        if hasattr(self, "spin_paper_slippage_bps")
        else Config.DEFAULT_PAPER_SLIPPAGE_BPS
    )
    if hasattr(svc, "set_cost_model"):
        svc.set_cost_model(fee_rate=float(fee_bps) / 10000.0, slippage_bps=float(slip_bps))
    return svc


def _seed_paper_balance_once(self):
    if not _is_paper_mode(self):
        return
    svc = _ensure_paper_service_state(self)
    if svc is None:
        return
    try:
        if hasattr(self, "_paper_seeded") and self._paper_seeded:
            return
        seed = float(getattr(self, "balance", 0.0) or 0.0)
        if seed <= 0 and getattr(self, "upbit", None) and getattr(self, "is_connected", False):
            api_balance = self._api_get_balance("KRW")
            if api_balance is not None:
                seed = float(api_balance)
        if seed <= 0:
            seed = _get_paper_seed_krw(self)
        if seed > 0:
            svc.seed_balance(seed)
            if float(getattr(self, "balance", 0.0) or 0.0) <= 0:
                self.balance = float(seed)
        self._paper_seeded = True
    except Exception:
        return
