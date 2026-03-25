from upbit_autotrader.controllers.trading_controller import TraderTradingController


REQUIRED_METHODS = [
    "login",
    "get_balance",
    "start_trading",
    "stop_trading",
    "_ensure_indicator_cache_state",
    "_ensure_order_stability_state",
    "_persist_reconciliation_state",
    "_load_reconciliation_state",
    "_transition_pending",
    "_register_manual_review",
    "_ops_alert",
    "_get_strategy_runtime_config",
    "_get_execution_config",
    "_place_buy_order",
    "_place_sell_order",
    "_safe_get_order",
    "_reconcile_pending_orders",
    "api_call_with_retry",
    "calculate_entry_score",
    "on_price_update",
    "_check_buy_condition",
    "_check_sell_condition",
    "execute_buy",
    "check_buy_execution",
    "execute_sell",
    "_execute_partial_sell",
    "_check_partial_sell_execution",
    "check_sell_execution",
]


def test_trading_controller_facade_keeps_expected_method_surface():
    missing = [name for name in REQUIRED_METHODS if not hasattr(TraderTradingController, name)]
    assert not missing, f"missing facade methods: {missing}"


def test_trading_controller_facade_methods_are_callable_descriptors():
    for name in REQUIRED_METHODS:
        attr = getattr(TraderTradingController, name)
        assert callable(attr), f"{name} should be callable"
