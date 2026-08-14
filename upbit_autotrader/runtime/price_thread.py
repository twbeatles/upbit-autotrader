from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional, cast

from PyQt6.QtCore import QThread, pyqtSignal

from upbit_autotrader.core.config import Config
from upbit_autotrader.services.pyupbit_compat import pyupbit_fallback

try:
    import pyupbit
except ImportError:
    pyupbit = pyupbit_fallback


import time
from upbit_autotrader.services.upbit_websocket import UpbitWebSocketClient


class PriceUpdateThread(QThread):
    """Background thread for real-time price updates via WebSocket with REST polling fallback."""
    price_updated = pyqtSignal(dict)
    order_event_received = pyqtSignal(dict)
    asset_event_received = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.coin_list = []
        self.is_running = False
        self._stop_event = threading.Event()
        self._coins_lock = threading.Lock()
        self._last_ws_ts = 0.0
        self._ws_client: Optional[UpbitWebSocketClient] = None

    def _on_ws_ticker(self, market: str, price: float, data: dict):
        self._last_ws_ts = time.time()
        self.price_updated.emit({market: price})

    def _on_ws_my_order(self, data: dict):
        # Emit Qt Signal for thread-safe cross-thread execution on main event loop
        self.order_event_received.emit(data)

    def _on_ws_my_asset(self, data: dict):
        # Emit Qt Signal for real-time asset balance updates
        self.asset_event_received.emit(data)

    def set_coins(self, coins):
        with self._coins_lock:
            self.coin_list = list(coins or [])
        if self._ws_client is not None:
            self._ws_client.set_markets(self.coin_list)

    def run(self):
        self._stop_event.clear()
        self.is_running = True

        # Initialize and start WebSocket if available
        parent = self.parent()
        access_key = ""
        secret_key = ""
        upbit_inst = getattr(parent, "upbit", None) if parent is not None else None
        if upbit_inst is not None:
            access_key = getattr(upbit_inst, "access_key", "") or ""
            secret_key = getattr(upbit_inst, "secret_key", "") or ""

        with self._coins_lock:
            coins = list(self.coin_list)

        try:
            self._ws_client = UpbitWebSocketClient(
                access_key=access_key,
                secret_key=secret_key,
                markets=coins,
                on_ticker=self._on_ws_ticker,
                on_my_order=self._on_ws_my_order,
                on_my_asset=self._on_ws_my_asset,
            )
            self._ws_client.start()
        except Exception as e:
            logging.warning(f"WebSocket client init failed, using REST only: {e}")
            self._ws_client = None

        while not self._stop_event.is_set():
            with self._coins_lock:
                coins = list(self.coin_list)
            if not coins:
                break

            # If WebSocket hasn't received data in the last 4 seconds, fallback to REST
            now_ts = time.time()
            ws_active = bool(self._ws_client and self._ws_client.is_connected() and (now_ts - self._last_ws_ts) < 4.0)

            if not ws_active:
                try:
                    ticker_arg = coins if len(coins) > 1 else coins[0]
                    prices = None
                    if upbit_inst is not None and hasattr(upbit_inst, "get_current_price") and callable(getattr(upbit_inst, "get_current_price")):
                        try:
                            prices = upbit_inst.get_current_price(ticker_arg)
                        except Exception:
                            prices = None
                    if prices is None and pyupbit is not None and pyupbit is not pyupbit_fallback:
                        prices = cast(Any, pyupbit).get_current_price(ticker_arg)

                    if prices:
                        payload = prices if isinstance(prices, dict) else {coins[0]: prices}
                        self.price_updated.emit(payload)
                except Exception as e:
                    logging.warning(f"price fetch failed: {e}")

            if self._stop_event.wait(Config.PRICE_UPDATE_INTERVAL):
                break

        if self._ws_client is not None:
            try:
                self._ws_client.stop()
            except Exception:
                pass
            self._ws_client = None

        self.is_running = False

    def stop(self):
        self.is_running = False
        self._stop_event.set()
        if self._ws_client is not None:
            try:
                self._ws_client.stop()
            except Exception:
                pass

