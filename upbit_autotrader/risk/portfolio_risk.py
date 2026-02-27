"""Portfolio-level risk snapshot and limit evaluation helpers."""

from dataclasses import dataclass
from typing import Dict, Any, Tuple, List

import numpy as np


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def resolve_drawdown_state(
    loss_rate_pct: float,
    enabled: bool = False,
    caution_pct: float = 3.0,
    defense_pct: float = 5.0,
    halt_pct: float = 8.0,
) -> str:
    if not enabled:
        return "normal"

    drawdown = max(0.0, -float(loss_rate_pct or 0.0))
    if drawdown >= float(halt_pct):
        return "halt"
    if drawdown >= float(defense_pct):
        return "defense"
    if drawdown >= float(caution_pct):
        return "caution"
    return "normal"


def _position_notional(pos: Dict[str, Any]) -> float:
    qty = _safe_float(pos.get("qty"), 0.0)
    buy_price = _safe_float(pos.get("buy_price"), 0.0)
    cur = _safe_float(pos.get("current_price"), 0.0)
    if qty <= 0:
        return 0.0
    basis = cur if cur > 0 else buy_price
    return max(0.0, qty * basis)


def _calc_unrealized_pnl(positions: Dict[str, Dict[str, Any]]) -> float:
    pnl = 0.0
    for pos in positions.values():
        qty = _safe_float(pos.get("qty"), 0.0)
        buy = _safe_float(pos.get("buy_price"), 0.0)
        cur = _safe_float(pos.get("current_price"), 0.0)
        if qty <= 0 or buy <= 0 or cur <= 0:
            continue
        pnl += (cur - buy) * qty
    return pnl


def _calc_correlation_exposure(
    positions: Dict[str, Dict[str, Any]],
    price_history: Dict[str, List[float]],
    window: int = 60,
    corr_threshold: float = 0.8,
) -> Tuple[float, float]:
    if not price_history:
        return 0.0, 0.0

    tickers = []
    returns = []
    notionals = {}
    for ticker, pos in positions.items():
        notional = _position_notional(pos)
        if notional <= 0:
            continue
        closes = list(price_history.get(ticker) or [])
        if len(closes) < max(5, window):
            continue
        arr = np.asarray(closes[-window:], dtype=float)
        if np.any(arr <= 0):
            continue
        ret = np.diff(arr) / arr[:-1]
        if len(ret) < 3:
            continue
        tickers.append(ticker)
        returns.append(ret)
        notionals[ticker] = notional

    if len(tickers) < 2:
        return 0.0, 0.0

    data = np.asarray(returns)
    corr = np.corrcoef(data)
    if corr.ndim != 2:
        return 0.0, 0.0

    max_abs_corr = 0.0
    correlated = set()
    n = len(tickers)
    for i in range(n):
        for j in range(i + 1, n):
            c = abs(float(corr[i, j]))
            max_abs_corr = max(max_abs_corr, c)
            if c >= corr_threshold:
                correlated.add(tickers[i])
                correlated.add(tickers[j])

    gross = sum(notionals.values())
    if gross <= 0:
        return 0.0, max_abs_corr
    correlated_notional = sum(notionals.get(t, 0.0) for t in correlated)
    return correlated_notional / gross * 100.0, max_abs_corr


def build_portfolio_risk_snapshot(
    *,
    initial_balance: float,
    realized_pnl: float,
    universe_positions: Dict[str, Dict[str, Any]],
    account_wide_positions: Dict[str, Dict[str, Any]],
    include_unrealized: bool = True,
    include_external_holdings: bool = True,
    drawdown_state_enabled: bool = False,
    dd_caution_pct: float = 3.0,
    dd_defense_pct: float = 5.0,
    dd_halt_pct: float = 8.0,
    corr_window: int = 60,
    price_history: Dict[str, List[float]] = None,
) -> Dict[str, Any]:
    realized = _safe_float(realized_pnl, 0.0)
    source_positions = account_wide_positions if include_external_holdings else universe_positions
    source_positions = dict(source_positions or {})
    universe_positions = dict(universe_positions or {})
    account_wide_positions = dict(account_wide_positions or {})

    unrealized = _calc_unrealized_pnl(source_positions) if include_unrealized else 0.0
    portfolio_pnl = realized + unrealized
    initial = max(0.0, _safe_float(initial_balance, 0.0))
    loss_rate = (portfolio_pnl / initial * 100.0) if initial > 0 else 0.0

    gross_exposure = sum(_position_notional(pos) for pos in account_wide_positions.values())
    corr_exposure, max_pair_corr = _calc_correlation_exposure(
        positions=account_wide_positions,
        price_history=price_history or {},
        window=max(5, int(corr_window or 60)),
    )
    risk_state = resolve_drawdown_state(
        loss_rate,
        enabled=drawdown_state_enabled,
        caution_pct=float(dd_caution_pct),
        defense_pct=float(dd_defense_pct),
        halt_pct=float(dd_halt_pct),
    )

    external = [
        t for t, pos in account_wide_positions.items()
        if t not in universe_positions and _safe_float(pos.get("qty"), 0.0) > 0
    ]

    return {
        "realized_pnl": realized,
        "unrealized_pnl": unrealized,
        "portfolio_pnl": portfolio_pnl,
        "loss_rate": loss_rate,
        "holdings_count": sum(1 for pos in account_wide_positions.values() if _safe_float(pos.get("qty"), 0.0) > 0),
        "external_holdings_count": len(external),
        "gross_exposure_krw": gross_exposure,
        "correlation_exposure_pct": corr_exposure,
        "max_pairwise_corr": max_pair_corr,
        "risk_state": risk_state,
    }


@dataclass
class RiskLimitConfig:
    max_daily_loss_pct: float = 5.0
    max_holdings: int = 5
    max_correlation_exposure_pct: float = 100.0


def evaluate_risk_limits(
    snapshot: Dict[str, Any],
    config: RiskLimitConfig,
    daily_loss_triggered: bool = False,
) -> Tuple[bool, bool, List[str]]:
    reasons: List[str] = []
    triggered = bool(daily_loss_triggered)
    loss_rate = _safe_float(snapshot.get("loss_rate"), 0.0)
    max_loss = -abs(_safe_float(config.max_daily_loss_pct, 5.0))
    if loss_rate <= max_loss:
        triggered = True
        reasons.append(f"loss_rate_limit:{loss_rate:.2f}%")

    holdings = int(_safe_float(snapshot.get("holdings_count"), 0.0))
    if holdings >= int(config.max_holdings):
        reasons.append(f"holdings_limit:{holdings}")

    corr_exp = _safe_float(snapshot.get("correlation_exposure_pct"), 0.0)
    if corr_exp > _safe_float(config.max_correlation_exposure_pct, 100.0):
        reasons.append(f"correlation_exposure_limit:{corr_exp:.2f}%")

    if str(snapshot.get("risk_state", "normal")) == "halt":
        reasons.append("drawdown_state_halt")

    allowed = len(reasons) == 0
    return allowed, triggered, reasons

