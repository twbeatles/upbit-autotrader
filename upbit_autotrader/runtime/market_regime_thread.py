"""Background thread for periodic market regime refresh."""

from __future__ import annotations

import logging
import threading

from PyQt6.QtCore import QThread, pyqtSignal

from upbit_autotrader.market_regime import build_market_regime_output, build_market_regime_snapshot


class MarketRegimeThread(QThread):
    regime_updated = pyqtSignal(object, object)

    def __init__(
        self,
        *,
        refresh_sec: int = 60,
        top_n: int = 20,
        use_fear_greed: bool = True,
        use_etf_flow: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.refresh_sec = max(5, int(refresh_sec))
        self.top_n = max(1, int(top_n))
        self.use_fear_greed = bool(use_fear_greed)
        self.use_etf_flow = bool(use_etf_flow)
        self._stop_event = threading.Event()
        self.last_snapshot = None
        self.last_output = None

    def run(self):
        self._stop_event.clear()
        while not self._stop_event.is_set():
            try:
                snapshot = build_market_regime_snapshot(
                    top_n=self.top_n,
                    use_fear_greed=self.use_fear_greed,
                    use_etf_flow=self.use_etf_flow,
                )
                output = build_market_regime_output(snapshot, use_overlay=self.use_etf_flow)
                self.last_snapshot = snapshot
                self.last_output = output
                self.regime_updated.emit(snapshot, output)
            except Exception as exc:  # pragma: no cover - defensive runtime path
                logging.warning("market regime refresh failed: %s", exc)
            if self._stop_event.wait(self.refresh_sec):
                break

    def stop(self):
        self._stop_event.set()
