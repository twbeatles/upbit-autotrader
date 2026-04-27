from __future__ import annotations

import time
from typing import Any, cast

# Runtime bindings injected by trading_controller facade
Config = cast(Any, None)
MarketRegimeThread = cast(Any, None)
build_neutral_market_regime_output = cast(Any, None)


def bind_runtime(**kwargs):
    globals().update(kwargs)


def _toggle(widget, default):
    return bool(widget.isChecked()) if widget is not None and hasattr(widget, "isChecked") else bool(default)


def _spin(widget, default):
    if widget is not None and hasattr(widget, "value"):
        return widget.value()
    return default


def _ensure_market_regime_state(self):
    if not hasattr(self, "market_regime_output") or self.market_regime_output is None:
        self.market_regime_output = build_neutral_market_regime_output()
    if not hasattr(self, "market_regime_snapshot"):
        self.market_regime_snapshot = None
    if not hasattr(self, "market_regime_snapshot_ts"):
        self.market_regime_snapshot_ts = 0.0
    if not hasattr(self, "_last_market_regime_log_state"):
        self._last_market_regime_log_state = None


def _get_market_regime_config(self):
    return {
        "use_market_regime_filter": _toggle(
            getattr(self, "chk_use_market_regime_filter", None),
            getattr(Config, "DEFAULT_USE_MARKET_REGIME_FILTER", False),
        ),
        "use_market_regime_risk_scaling": _toggle(
            getattr(self, "chk_use_market_regime_risk_scaling", None),
            getattr(Config, "DEFAULT_USE_MARKET_REGIME_RISK_SCALING", False),
        ),
        "market_regime_min_score": float(
            _spin(getattr(self, "spin_market_regime_min_score", None), getattr(Config, "DEFAULT_MARKET_REGIME_MIN_SCORE", 55.0))
        ),
        "market_regime_refresh_sec": int(
            _spin(getattr(self, "spin_market_regime_refresh_sec", None), getattr(Config, "DEFAULT_MARKET_REGIME_REFRESH_SEC", 60))
        ),
        "market_regime_top_n": int(
            _spin(getattr(self, "spin_market_regime_top_n", None), getattr(Config, "DEFAULT_MARKET_REGIME_TOP_N", 20))
        ),
        "market_regime_use_fear_greed": _toggle(
            getattr(self, "chk_market_regime_use_fear_greed", None),
            getattr(Config, "DEFAULT_MARKET_REGIME_USE_FEAR_GREED", True),
        ),
        "market_regime_use_etf_flow": _toggle(
            getattr(self, "chk_market_regime_use_etf_flow", None),
            getattr(Config, "DEFAULT_MARKET_REGIME_USE_ETF_FLOW", False),
        ),
        "fail_closed_on_stale_market_regime": _toggle(
            getattr(self, "chk_fail_closed_on_stale_market_regime", None),
            getattr(Config, "DEFAULT_FAIL_CLOSED_ON_STALE_MARKET_REGIME", False),
        ),
    }


def _get_market_regime_output(self):
    _ensure_market_regime_state(self)
    return self.market_regime_output


def _capture_market_regime_fields(self, info=None):
    output = _get_market_regime_output(self)
    snapshot_ts = str(getattr(getattr(self, "market_regime_snapshot", None), "as_of", "") or "")
    fields = {
        "market_regime_score": float(getattr(output, "market_regime_score", 50.0) or 50.0),
        "market_regime_label": str(getattr(output, "label", "neutral") or "neutral"),
        "market_regime_ts": snapshot_ts,
    }
    if isinstance(info, dict):
        info.update(
            {
                "last_market_regime_score": fields["market_regime_score"],
                "last_market_regime_label": fields["market_regime_label"],
                "last_market_regime_ts": fields["market_regime_ts"],
            }
        )
    return fields


def _resolve_market_regime_fields(self, pending=None, info=None):
    info = info if isinstance(info, dict) else {}
    snapshot_ts = str(getattr(getattr(self, "market_regime_snapshot", None), "as_of", "") or "")
    fields = {
        "market_regime_score": float(info.get("last_market_regime_score", 50.0) or 50.0),
        "market_regime_label": str(info.get("last_market_regime_label", "neutral") or "neutral"),
        "market_regime_ts": str(info.get("last_market_regime_ts", snapshot_ts) or snapshot_ts),
    }
    if isinstance(pending, dict):
        fields["market_regime_score"] = float(pending.get("market_regime_score", fields["market_regime_score"]) or fields["market_regime_score"])
        fields["market_regime_label"] = str(pending.get("market_regime_label", fields["market_regime_label"]) or fields["market_regime_label"])
        fields["market_regime_ts"] = str(pending.get("market_regime_ts", fields["market_regime_ts"]) or fields["market_regime_ts"])
    return fields


def _apply_market_regime_filter(self, ticker):
    cfg = _get_market_regime_config(self)
    if not cfg["use_market_regime_filter"]:
        return True
    output = _get_market_regime_output(self)
    stale = {str(v) for v in (getattr(output, "stale_components", []) or [])}
    if cfg.get("fail_closed_on_stale_market_regime") and stale.intersection({"local_breadth", "btc_trend_vol"}):
        if hasattr(self, "log"):
            self.log(f"[{ticker}] market regime stale 차단: {','.join(sorted(stale))}")
        return False
    score = float(getattr(output, "market_regime_score", 50.0) or 50.0)
    threshold = float(cfg["market_regime_min_score"])
    if score >= threshold:
        return True
    if hasattr(self, "log"):
        self.log(f"[{ticker}] market regime 보류: {score:.1f} < {threshold:.1f} ({getattr(output, 'label', 'neutral')})")
    return False


def _apply_market_regime_risk_scaling(self, order_notional_krw):
    cfg = _get_market_regime_config(self)
    amount = max(0.0, float(order_notional_krw or 0.0))
    if not cfg["use_market_regime_risk_scaling"]:
        return amount
    output = _get_market_regime_output(self)
    multiplier = float(getattr(output, "risk_multiplier", 1.0) or 1.0)
    return max(0.0, amount * multiplier)


def _update_market_regime_status(self):
    output = _get_market_regime_output(self)
    label_widget = getattr(self, "status_market_regime", None)
    if label_widget is None or not hasattr(label_widget, "setText"):
        return
    label = str(getattr(output, "label", "neutral") or "neutral")
    score = float(getattr(output, "market_regime_score", 50.0) or 50.0)
    stale = tuple(sorted(getattr(output, "stale_components", []) or []))
    suffix = f" stale:{len(stale)}" if stale else ""
    label_widget.setText(f"MR: {label} {score:.1f}{suffix}")


def _on_market_regime_update(self, snapshot, output):
    _ensure_market_regime_state(self)
    prev = getattr(self, "market_regime_output", None)
    prev_label = str(getattr(prev, "label", "") or "")
    prev_score = float(getattr(prev, "market_regime_score", 50.0) or 50.0) if prev is not None else 50.0
    prev_stale = tuple(sorted(getattr(prev, "stale_components", []) or [])) if prev is not None else ()

    self.market_regime_snapshot = snapshot
    self.market_regime_output = output
    self.market_regime_snapshot_ts = time.time()
    _update_market_regime_status(self)

    label = str(getattr(output, "label", "neutral") or "neutral")
    score = float(getattr(output, "market_regime_score", 50.0) or 50.0)
    stale = tuple(sorted(getattr(output, "stale_components", []) or []))
    should_log = (label != prev_label) or (stale != prev_stale) or (abs(score - prev_score) >= 5.0)
    if should_log and hasattr(self, "log"):
        stale_text = f", stale={','.join(stale)}" if stale else ""
        self.log(f"🌐 Market regime 업데이트: {label} {score:.1f}{stale_text}")
