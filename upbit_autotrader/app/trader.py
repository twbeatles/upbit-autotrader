"""
Upbit Pro Algo-Trader v3.1
Facade entrypoint for modularized trading controllers.
"""

import sys

try:
    import pandas as pd  # noqa: F401
    import pyupbit  # noqa: F401
except ImportError:
    print("pyupbit library is required. Install it with: pip install pyupbit")
    sys.exit(1)

from PyQt6.QtWidgets import QApplication, QMainWindow

from upbit_autotrader.app import bootstrap_ops as _bootstrap_ops, runtime_ops as _runtime_ops
from upbit_autotrader.controllers.batch_controller import TraderBatchController
from upbit_autotrader.controllers.history_controller import TraderHistoryController
from upbit_autotrader.controllers.settings_controller import TraderSettingsController
from upbit_autotrader.controllers.trading_controller import TraderTradingController
from upbit_autotrader.controllers.ui_controller import TraderUIController


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
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    trader = UpbitProTrader()
    trader.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
