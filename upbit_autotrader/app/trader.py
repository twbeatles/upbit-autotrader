"""
Upbit Pro Algo-Trader v3.1
Facade entrypoint for modularized trading controllers.
"""

import sys

try:
    import pandas as pd  # noqa: F401
    import pyupbit  # noqa: F401
except ImportError:
    pyupbit = None  # type: ignore[assignment]

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow

from upbit_autotrader.app import bootstrap_ops as _bootstrap_ops, runtime_ops as _runtime_ops
from upbit_autotrader.controllers.batch_controller import TraderBatchController
from upbit_autotrader.controllers.history_controller import TraderHistoryController
from upbit_autotrader.controllers.settings_controller import TraderSettingsController
from upbit_autotrader.controllers.trading_controller import TraderTradingController
from upbit_autotrader.controllers.ui_controller import TraderUIController
from upbit_autotrader.ui.theme import configure_main_window, setup_app_theme


class UpbitProTrader(
    TraderUIController,
    TraderSettingsController,
    TraderHistoryController,
    TraderTradingController,
    TraderBatchController,
    QMainWindow,
):
    setup_logging = _bootstrap_ops.setup_logging
    setup_timers = _bootstrap_ops.setup_timers

    _create_price_thread = _runtime_ops._create_price_thread
    _restart_price_thread = _runtime_ops._restart_price_thread
    _create_market_regime_thread = _runtime_ops._create_market_regime_thread
    _stop_market_regime_thread = _runtime_ops._stop_market_regime_thread
    _restart_market_regime_thread = _runtime_ops._restart_market_regime_thread
    on_timer_tick = _runtime_ops.on_timer_tick
    _reset_daily_stats = _runtime_ops._reset_daily_stats
    closeEvent = _runtime_ops.closeEvent

    def __init__(self):
        super().__init__()
        _bootstrap_ops.bootstrap_trader(self)


def main():
    # Fractional Windows scaling (125%/150%) snaps to integer factors by
    # default, which blurs custom-painted widgets. PassThrough keeps the
    # real scale factor so the chart renders crisply on HiDPI displays.
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    setup_app_theme(app)
    trader = UpbitProTrader()
    configure_main_window(trader)
    trader.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
