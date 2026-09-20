"""Backward-compat shim: implementation lives in :mod:`execution` subpackage (SOLID SRP split)."""
from __future__ import annotations

from upbit_autotrader.controllers.trading_parts.execution import (
    _buy_order_has_fill,
    _check_partial_sell_execution,
    _execute_partial_sell,
    _extract_market_state,
    _extract_min_total,
    _handle_ws_order_event,
    _market_regime_fields_dict,
    _reconcile_pending_orders,
    _reconcile_terminal_pending,
    _resolve_timeout_pending,
    _run_next_twap_buy_slice,
    _safe_float,
    _schedule_next_twap_buy_slice,
    _sell_order_has_fill,
    _start_twap_buy,
    _supports_order_type,
    _validate_live_order_request,
    check_buy_execution,
    check_sell_execution,
    execute_buy,
    execute_sell,
)

__all__ = ["_buy_order_has_fill","_check_partial_sell_execution","_execute_partial_sell","_extract_market_state","_extract_min_total","_handle_ws_order_event","_market_regime_fields_dict","_reconcile_pending_orders","_reconcile_terminal_pending","_resolve_timeout_pending","_run_next_twap_buy_slice","_safe_float","_schedule_next_twap_buy_slice","_sell_order_has_fill","_start_twap_buy","_supports_order_type","_validate_live_order_request","check_buy_execution","check_sell_execution","execute_buy","execute_sell"]
