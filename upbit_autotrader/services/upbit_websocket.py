"""
Upbit WebSocket client supporting both Public (ticker) and Private (myOrder, myAsset) streams.
"""

from __future__ import annotations

import datetime
import json
import logging
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

import jwt

logger = logging.getLogger(__name__)

try:
    import websocket
except ImportError:
    websocket = None


class UpbitWebSocketClient:
    """
    WebSocket client for Upbit real-time market data and private order events.
    """

    PUBLIC_URL = "wss://api.upbit.com/websocket/v1"
    PRIVATE_URL = "wss://api.upbit.com/websocket/v1/private"

    def __init__(
        self,
        access_key: str = "",
        secret_key: str = "",
        markets: Optional[List[str]] = None,
        on_ticker: Optional[Callable[[str, float, Dict[str, Any]], None]] = None,
        on_my_order: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_my_asset: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ):
        self.access_key = str(access_key or "").strip()
        self.secret_key = str(secret_key or "").strip()
        self.markets = list(markets or [])
        self.on_ticker = on_ticker
        self.on_my_order = on_my_order
        self.on_my_asset = on_my_asset
        self.on_error = on_error

        self._ws: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_connected = False
        self._lock = threading.Lock()

    def set_markets(self, markets: List[str]) -> None:
        with self._lock:
            self.markets = list(markets or [])
        if self._is_connected and self._ws:
            try:
                self._send_subscribe()
            except Exception as e:
                logger.warning(f"WebSocket resubscribe failed: {e}")

    def is_connected(self) -> bool:
        return self._is_connected

    def _generate_jwt_token(self) -> str:
        payload = {
            "access_key": self.access_key,
            "nonce": str(uuid.uuid4()),
            "timestamp": int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp() * 1000),
        }
        token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return f"Bearer {token}"

    def _get_subscribe_payload(self) -> str:
        ticket = f"agy-{uuid.uuid4().hex[:12]}"
        with self._lock:
            codes = list(self.markets) if self.markets else ["KRW-BTC"]

        fields: List[Dict[str, Any]] = [{"ticket": ticket}]

        # Ticker subscription
        fields.append({"type": "ticker", "codes": codes})

        # Private streams if keys available
        if self.access_key and self.secret_key:
            fields.append({"type": "myOrder", "codes": codes})
            fields.append({"type": "myAsset"})

        fields.append({"format": "DEFAULT"})
        return json.dumps(fields)

    def _send_subscribe(self) -> None:
        if self._ws:
            payload = self._get_subscribe_payload()
            self._ws.send(payload)

    def start(self) -> None:
        if websocket is None:
            logger.warning("websocket-client library is not installed.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="UpbitWebSocketThread")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._is_connected = False
        ws = self._ws
        if ws is not None:
            try:
                setattr(ws, "keep_running", False)
                ws.close()
            except Exception:
                pass
        if self._thread and self._thread.is_alive() and threading.current_thread() != self._thread:
            self._thread.join(timeout=0.1)

    def _run_loop(self) -> None:
        backoff = 1.0
        while not self._stop_event.is_set():
            try:
                if websocket is None:
                    break
                is_private = bool(self.access_key and self.secret_key)
                url = self.PRIVATE_URL if is_private else self.PUBLIC_URL
                headers = []
                if is_private:
                    headers.append(f"Authorization: {self._generate_jwt_token()}")

                self._ws = websocket.WebSocketApp(
                    url,
                    header=headers,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_ws_error,
                    on_close=self._on_close,
                )
                self._ws.run_forever(ping_interval=60, ping_timeout=10)
            except Exception as exc:
                if self.on_error:
                    self.on_error(exc)
                logger.warning(f"WebSocket loop error: {exc}")

            if self._stop_event.is_set() or self._stop_event.wait(backoff):
                break

            backoff = min(30.0, backoff * 1.5)

    def _on_open(self, ws: Any) -> None:
        self._is_connected = True
        try:
            self._send_subscribe()
            logger.info("Upbit WebSocket connected and subscribed.")
        except Exception as e:
            logger.warning(f"WebSocket subscription error on open: {e}")

    def _on_message(self, ws: Any, message: Any) -> None:
        try:
            if isinstance(message, bytes):
                text = message.decode("utf-8")
            else:
                text = str(message)
            data = json.loads(text)
        except Exception:
            return

        if not isinstance(data, dict):
            return

        msg_type = str(data.get("type", "")).lower()
        if msg_type == "ticker":
            market = str(data.get("code", "")).strip()
            price = float(data.get("trade_price", 0.0) or 0.0)
            if market and price > 0 and self.on_ticker:
                try:
                    self.on_ticker(market, price, data)
                except Exception as e:
                    logger.warning(f"Error in on_ticker callback: {e}")
        elif msg_type == "myorder":
            if self.on_my_order:
                try:
                    self.on_my_order(data)
                except Exception as e:
                    logger.warning(f"Error in on_my_order callback: {e}")
        elif msg_type == "myasset":
            if self.on_my_asset:
                try:
                    self.on_my_asset(data)
                except Exception as e:
                    logger.warning(f"Error in on_my_asset callback: {e}")

    def _on_ws_error(self, ws: Any, error: Any) -> None:
        self._is_connected = False
        if isinstance(error, Exception) and self.on_error:
            self.on_error(error)

    def _on_close(self, ws: Any, close_status_code: Any, close_msg: Any) -> None:
        self._is_connected = False
