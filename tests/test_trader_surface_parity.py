import builtins
import importlib
import sys
from unittest.mock import patch


REQUIRED_METHODS = [
    "init_ui",
    "create_dashboard",
    "create_tab_widget",
    "create_strategy_tab",
    "create_advanced_tab",
    "create_statistics_tab",
    "create_history_tab",
    "create_splitter",
    "create_statusbar",
    "create_menu_bar",
    "setup_tray",
    "show_help",
    "show_settings",
    "open_preset_manager",
    "save_settings",
    "load_settings",
    "set_startup_registry",
    "setup_timers",
    "start_trading",
    "stop_trading",
    "on_price_update",
    "execute_buy",
    "execute_sell",
    "check_buy_execution",
    "check_sell_execution",
    "execute_batch_buy",
    "execute_batch_sell",
    "execute_emergency_close",
    "add_trade_record",
    "save_trade_history",
    "_update_statistics",
    "log",
]


def test_upbit_pro_trader_surface_methods_exist():
    trader_mod = importlib.import_module("upbit_trader")
    missing = [name for name in REQUIRED_METHODS if not hasattr(trader_mod.UpbitProTrader, name)]
    assert not missing, f"missing methods: {missing}"


def test_dialog_import_chain_primary_path():
    ui_mod = importlib.import_module("upbit_autotrader.controllers.ui_controller")
    assert ui_mod.PresetManagerDialogV3 is not None
    assert ui_mod.HelpDialogV3 is not None
    assert ui_mod.SettingsDialogV3 is not None


def test_dialog_import_chain_fallback_path():
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "upbit_autotrader.ui.dialogs":
            raise ImportError("forced fallback path")
        return real_import(name, globals, locals, fromlist, level)

    with patch("builtins.__import__", side_effect=fake_import):
        sys.modules.pop("upbit_autotrader.controllers.ui_controller", None)
        fallback_mod = importlib.import_module("upbit_autotrader.controllers.ui_controller")

    assert fallback_mod.PresetManagerDialogV3 is None
    assert fallback_mod.HelpDialogV3 is None
    assert fallback_mod.SettingsDialogV3 is None
    assert fallback_mod.PresetManagerDialog is not None
    assert fallback_mod.HelpDialog is not None
    assert fallback_mod.SettingsDialog is not None

    # restore the normal import state for downstream tests
    sys.modules.pop("upbit_autotrader.controllers.ui_controller", None)
    importlib.import_module("upbit_autotrader.controllers.ui_controller")


