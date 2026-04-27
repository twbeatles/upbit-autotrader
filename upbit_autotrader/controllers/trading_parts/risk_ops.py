from __future__ import annotations

from typing import Any, cast

# Runtime bindings injected by trading_controller facade
Config = cast(Any, None)
RiskLimitConfig = cast(Any, None)
build_portfolio_risk_snapshot = cast(Any, None)
evaluate_risk_limits = cast(Any, None)
pyupbit = cast(Any, None)
time = cast(Any, None)


def bind_runtime(**kwargs):
    globals().update(kwargs)



def _get_risk_snapshot(self, force=False):
    self._ensure_order_stability_state()
    now_ts = time.time()
    ttl = float(getattr(Config, "RISK_SNAPSHOT_TTL_SEC", 5))
    cached = self._risk_snapshot_cache.get("value")
    cached_ts = float(self._risk_snapshot_cache.get("ts", 0.0) or 0.0)
    if not force and cached is not None and (now_ts - cached_ts) < ttl:
        return dict(cached)

    realized_pnl = float(getattr(self, "total_realized_profit", 0.0) or 0.0)
    universe_positions = {}
    for ticker, info in getattr(self, "universe", {}).items():
        qty = float(info.get("qty", 0.0) or 0.0)
        if qty <= 0:
            continue
        universe_positions[ticker] = {
            "qty": qty,
            "buy_price": float(info.get("buy_price", 0.0) or 0.0),
            "current_price": float(info.get("current", 0.0) or 0.0),
        }

    account_wide_positions = dict(universe_positions)
    account_holdings = self._fetch_account_holdings()
    for ticker, h in self._build_holdings_map(account_holdings).items():
        qty = float(h.get("qty", 0.0) or 0.0)
        if qty <= 0:
            continue
        payload = {
            "qty": qty,
            "buy_price": float(h.get("buy_price", 0.0) or 0.0),
            "current_price": float(h.get("current_price", 0.0) or 0.0),
        }
        prev = account_wide_positions.get(ticker, {})
        if payload["buy_price"] <= 0:
            payload["buy_price"] = float(prev.get("buy_price", 0.0) or 0.0)
        if payload["current_price"] <= 0:
            payload["current_price"] = float(prev.get("current_price", 0.0) or 0.0)
        account_wide_positions[ticker] = payload

    equity_info = (
        self._calculate_current_equity(account_wide_positions)
        if hasattr(self, "_calculate_current_equity")
        else {}
    )
    if float(getattr(self, "daily_start_equity_krw", 0.0) or 0.0) <= 0:
        self.daily_start_equity_krw = float(equity_info.get("equity_krw", getattr(self, "initial_balance", 0.0)) or 0.0)

    price_history = {}
    corr_limit = self._max_correlation_exposure_pct()
    if corr_limit < 100.0 and pyupbit is not None and account_wide_positions:
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()] if hasattr(self, "combo_candle") else "minute240"
        corr_window = max(20, self._portfolio_corr_window())
        max_tickers = max(1, int(getattr(Config, "DEFAULT_CORRELATION_MAX_TICKERS", 20)))
        ranked = sorted(
            account_wide_positions.items(),
            key=lambda kv: float(kv[1].get("qty", 0.0) or 0.0)
            * max(
                float(kv[1].get("current_price", 0.0) or 0.0),
                float(kv[1].get("buy_price", 0.0) or 0.0),
            ),
            reverse=True,
        )
        for ticker, _pos in ranked[:max_tickers]:
            try:
                df = pyupbit.get_ohlcv(ticker, interval=interval, count=corr_window + 1)
                if df is None or len(df) < corr_window:
                    continue
                price_history[ticker] = [float(v) for v in df["close"].tolist() if float(v) > 0]
            except Exception:
                continue

    dd_caution, dd_defense, dd_halt = self._drawdown_thresholds()
    snapshot = build_portfolio_risk_snapshot(
        initial_balance=float(getattr(self, "initial_balance", 0.0) or 0.0),
        realized_pnl=realized_pnl,
        universe_positions=universe_positions,
        account_wide_positions=account_wide_positions,
        equity_krw=float(equity_info.get("equity_krw", 0.0) or 0.0),
        cash_krw=float(equity_info.get("cash_krw", getattr(self, "balance", 0.0)) or 0.0),
        reserved_krw=float(equity_info.get("reserved_krw", 0.0) or 0.0),
        daily_start_equity_krw=float(getattr(self, "daily_start_equity_krw", 0.0) or 0.0),
        include_unrealized=self._risk_include_unrealized(),
        include_external_holdings=self._risk_include_external_holdings(),
        drawdown_state_enabled=self._drawdown_state_enabled(),
        dd_caution_pct=float(dd_caution),
        dd_defense_pct=float(dd_defense),
        dd_halt_pct=float(dd_halt),
        corr_window=self._portfolio_corr_window(),
        price_history=price_history,
    )
    self._risk_snapshot_cache = {"ts": now_ts, "value": snapshot}
    return dict(snapshot)


def check_risk_limits(self):
    """리스크 한도 체크"""
    if not self.chk_use_risk.isChecked():
        return True

    snapshot = self._get_risk_snapshot(force=False)
    allowed, triggered, reasons = evaluate_risk_limits(
        snapshot=snapshot,
        config=RiskLimitConfig(
            max_daily_loss_pct=float(self.spin_max_loss.value()),
            max_holdings=int(self.spin_max_holdings.value()),
            max_correlation_exposure_pct=float(self._max_correlation_exposure_pct()),
        ),
        daily_loss_triggered=bool(getattr(self, "daily_loss_triggered", False)),
    )
    if triggered and not self.daily_loss_triggered:
        self.daily_loss_triggered = True
        loss_rate = float(snapshot.get("loss_rate", 0.0) or 0.0)
        self._ops_alert(
            level="warning",
            message=f"🛑 일일 손실 한도 도달! ({loss_rate:.2f}%)",
            key="risk_limit:daily_loss",
            cooldown=20,
        )
    if not allowed and reasons:
        self._ops_alert(
            level="warning",
            message=f"⚠️ 리스크 제한으로 진입 보류 ({', '.join(reasons[:2])})",
            key=f"risk_limit:{'|'.join(reasons)}",
            cooldown=10,
        )
    return bool(allowed)
