import importlib


def test_legacy_module_wrappers_alias_refactored_modules():
    pairs = [
        (
            "upbit_trader_trading_controller",
            "upbit_autotrader.controllers.trading_controller",
            "TraderTradingController",
        ),
        (
            "upbit_trader_batch_controller",
            "upbit_autotrader.controllers.batch_controller",
            "TraderBatchController",
        ),
        (
            "upbit_order_service",
            "upbit_autotrader.services.order_service",
            "UpbitOrderService",
        ),
        (
            "upbit_strategy_engine",
            "upbit_autotrader.strategies.engine",
            "StrategyEngine",
        ),
    ]

    for legacy_mod, ref_mod, symbol in pairs:
        legacy = importlib.import_module(legacy_mod)
        refactored = importlib.import_module(ref_mod)
        assert getattr(legacy, symbol) is getattr(refactored, symbol)


def test_legacy_entrypoint_exports_main_trader_class():
    legacy_entry = importlib.import_module("upbit_trader")
    ref_entry = importlib.import_module("upbit_autotrader.app.trader")
    assert legacy_entry.UpbitProTrader is ref_entry.UpbitProTrader
