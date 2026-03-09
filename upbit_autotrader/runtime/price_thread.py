import logging
import threading
from typing import Any, cast

from PyQt6.QtCore import QThread, pyqtSignal

from upbit_autotrader.core.config import Config

try:
    import pyupbit
except ImportError:
    pyupbit = cast(Any, None)


class PriceUpdateThread(QThread):
    """Background thread for polling current prices."""
    price_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.coin_list = []
        self.is_running = False
        self._stop_event = threading.Event()
        self._coins_lock = threading.Lock()

    def set_coins(self, coins):
        with self._coins_lock:
            self.coin_list = list(coins or [])

    def run(self):
        self._stop_event.clear()
        self.is_running = True
        while not self._stop_event.is_set():
            with self._coins_lock:
                coins = list(self.coin_list)
            if not coins:
                break
            try:
                ticker_arg = coins if len(coins) > 1 else coins[0]
                prices = cast(Any, pyupbit).get_current_price(ticker_arg)
                if prices:
                    payload = prices if isinstance(prices, dict) else {coins[0]: prices}
                    self.price_updated.emit(payload)
            except Exception as e:
                logging.warning(f"price fetch failed: {e}")
            if self._stop_event.wait(Config.PRICE_UPDATE_INTERVAL):
                break
        self.is_running = False

    def stop(self):
        self.is_running = False
        self._stop_event.set()

