"""Legacy wrapper for upbit_websocket."""

import sys
from upbit_autotrader.services.upbit_websocket import UpbitWebSocketClient

sys.modules[__name__] = sys.modules["upbit_autotrader.services.upbit_websocket"]
