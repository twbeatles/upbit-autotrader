"""Per-row quick trade buttons for the holdings table (cols 10/11).

Buttons delegate to the order ticket flow (confirm gate included):
BUY sizes from balance x betting ratio, SELL uses the row holding qty.
"""
from PyQt6.QtWidgets import QPushButton

from upbit_autotrader.core.config import Config

BUY_COL = 10
SELL_COL = 11


def attach_row_trade_buttons(self, row: int, ticker: str) -> bool:
    table = getattr(self, "table", None)
    if table is None or not hasattr(table, "setCellWidget"):
        return False
    ticker = str(ticker or "").strip()
    if not ticker:
        return False
    btn_buy = QPushButton("매수")
    btn_buy.setProperty("tradeBuy", True)
    btn_buy.setToolTip(f"{ticker} 티켓 매수 (확인 게이트 적용)")
    btn_buy.clicked.connect(lambda _=False, t=ticker: row_quick_buy(self, t))
    btn_sell = QPushButton("매도")
    btn_sell.setProperty("tradeSell", True)
    btn_sell.setToolTip(f"{ticker} 보유수량 티켓 매도 (확인 게이트 적용)")
    btn_sell.clicked.connect(lambda _=False, t=ticker: row_quick_sell(self, t))
    try:
        table.setCellWidget(row, BUY_COL, btn_buy)
        table.setCellWidget(row, SELL_COL, btn_sell)
    except Exception:
        return False
    return True


def _sync_ticket(self, ticker: str, amount: float) -> bool:
    combo = getattr(self, "combo_ticket_symbol", None)
    spin = getattr(self, "spin_ticket_amount", None)
    if combo is None or spin is None:
        return False
    try:
        if hasattr(combo, "setCurrentText"):
            combo.setCurrentText(ticker)
        if hasattr(combo, "findText") and hasattr(combo, "count"):
            idx = combo.findText(ticker)
            if idx < 0 and hasattr(combo, "addItem"):
                combo.addItem(ticker)
                combo.setCurrentText(ticker)
        spin.setValue(max(0.0, float(amount)))
    except Exception:
        return False
    return True


def _default_buy_amount(self) -> float:
    try:
        balance = float(getattr(self, "balance", 0.0) or 0.0)
    except (TypeError, ValueError):
        balance = 0.0
    spin = getattr(self, "spin_betting", None)
    try:
        ratio = float(spin.value()) if spin is not None and hasattr(spin, "value") else float(Config.DEFAULT_BETTING_RATIO)
    except (TypeError, ValueError):
        ratio = float(Config.DEFAULT_BETTING_RATIO)
    return max(0.0, balance * ratio / 100.0)


def row_quick_buy(self, ticker: str) -> bool:
    """행 매수: 티켓에 종목/금액을 채우고 티켓 주문 플로우로 실행."""
    from upbit_autotrader.controllers.ui_parts import order_ticket_ops as _ticket_ops
    ticker = str(ticker or "").strip()
    if not ticker:
        return False
    if not _sync_ticket(self, ticker, _default_buy_amount(self)):
        return False
    try:
        return bool(_ticket_ops.submit_ticket_order(self, "BUY"))
    except AttributeError:
        return False


def row_quick_sell(self, ticker: str) -> bool:
    """행 매도: 보유수량을 티켓에 채우고 티켓 주문 플로우로 실행."""
    from upbit_autotrader.controllers.ui_parts import order_ticket_ops as _ticket_ops
    ticker = str(ticker or "").strip()
    if not ticker:
        return False
    universe = getattr(self, "universe", None)
    qty = 0.0
    if isinstance(universe, dict) and isinstance(universe.get(ticker), dict):
        try:
            qty = float(universe[ticker].get("qty", 0.0) or 0.0)
        except (TypeError, ValueError):
            qty = 0.0
    if qty <= 0:
        log = getattr(self, "log", None)
        if callable(log):
            log(f"[WARN] {ticker} 보유수량이 없어 매도할 수 없습니다.")
        return False
    if not _sync_ticket(self, ticker, qty):
        return False
    try:
        return bool(_ticket_ops.submit_ticket_order(self, "SELL"))
    except AttributeError:
        return False
