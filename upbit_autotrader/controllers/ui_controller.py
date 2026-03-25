from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QDialog, QMenu, QMessageBox, QSystemTrayIcon

from upbit_autotrader.controllers._type_support import ControllerTypeBase
from upbit_autotrader.controllers.ui_parts import (
    dashboard_ops as _dashboard_ops,
    layout_ops as _layout_ops,
    menu_tray_ops as _menu_tray_ops,
    preset_ops as _preset_ops,
    strategy_tab_ops as _strategy_tab_ops,
)
from upbit_autotrader.controllers.ui_sections import build_advanced_tab, build_ops_tab
from upbit_autotrader.core.config import Config
from upbit_autotrader.ui.dialog_fallbacks import HelpDialog, PresetManagerDialog, SettingsDialog

try:
    from upbit_autotrader.ui.dialogs import (
        DARK_STYLESHEET,
        HelpDialog as HelpDialogV3,
        PresetManagerDialog as PresetManagerDialogV3,
        SettingsDialog as SettingsDialogV3,
    )
except ImportError:
    DARK_STYLESHEET = ""
    HelpDialogV3 = None
    PresetManagerDialogV3 = None
    SettingsDialogV3 = None

try:
    from upbit_autotrader.analytics.trading_analytics import UpbitTradingAnalytics  # noqa: F401
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False

try:
    from upbit_autotrader.backtesting.backtester import UpbitBacktestEngine, volatility_breakout_strategy  # noqa: F401
    BACKTESTER_AVAILABLE = True
except ImportError:
    BACKTESTER_AVAILABLE = False


class TraderUIController(ControllerTypeBase):
    create_dashboard = _dashboard_ops.create_dashboard
    create_tab_widget = _layout_ops.create_tab_widget
    create_strategy_tab = _strategy_tab_ops.create_strategy_tab
    create_statistics_tab = _dashboard_ops.create_statistics_tab
    create_splitter = _layout_ops.create_splitter
    create_statusbar = _dashboard_ops.create_statusbar

    def init_ui(self):
        self._dark_stylesheet = DARK_STYLESHEET
        return _layout_ops.init_ui(self)

    def create_ops_tab(self):
        return build_ops_tab(self)

    def create_advanced_tab(self):
        return build_advanced_tab(self)

    def _bind_menu_runtime(self):
        _menu_tray_ops.bind_runtime(
            Config=Config,
            QAction=QAction,
            QMenu=QMenu,
            QMessageBox=QMessageBox,
            QSystemTrayIcon=QSystemTrayIcon,
            ANALYTICS_AVAILABLE=ANALYTICS_AVAILABLE,
            BACKTESTER_AVAILABLE=BACKTESTER_AVAILABLE,
        )

    def create_menu_bar(self):
        self._bind_menu_runtime()
        return _menu_tray_ops.create_menu_bar(self)

    def setup_tray(self):
        self._bind_menu_runtime()
        return _menu_tray_ops.setup_tray(self)

    def on_tray_activated(self, reason):
        self._bind_menu_runtime()
        return _menu_tray_ops.on_tray_activated(self, reason)

    def show_from_tray(self):
        self._bind_menu_runtime()
        return _menu_tray_ops.show_from_tray(self)

    def force_quit(self):
        self._bind_menu_runtime()
        return _menu_tray_ops.force_quit(self)

    def _bind_preset_runtime(self):
        _preset_ops.bind_runtime(
            Config=Config,
            QDialog=QDialog,
            PresetManagerDialog=PresetManagerDialog,
            PresetManagerDialogV3=PresetManagerDialogV3,
            HelpDialog=HelpDialog,
            HelpDialogV3=HelpDialogV3,
            SettingsDialog=SettingsDialog,
            SettingsDialogV3=SettingsDialogV3,
        )

    def open_preset_manager(self):
        self._bind_preset_runtime()
        return _preset_ops.open_preset_manager(self)

    def apply_preset_values(self, preset):
        self._bind_preset_runtime()
        return _preset_ops.apply_preset_values(self, preset)

    def _paper_no_login_allowed(self):
        self._bind_preset_runtime()
        return _preset_ops._paper_no_login_allowed(self)

    def refresh_trade_action_buttons(self):
        self._bind_preset_runtime()
        return _preset_ops.refresh_trade_action_buttons(self)

    def show_help(self):
        self._bind_preset_runtime()
        return _preset_ops.show_help(self)

    def show_settings(self):
        self._bind_preset_runtime()
        return _preset_ops.show_settings(self)
