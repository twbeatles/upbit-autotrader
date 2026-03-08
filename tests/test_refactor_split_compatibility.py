from unittest.mock import patch

import pandas as pd

from upbit_autotrader.controllers.trading_controller import TraderTradingController
from upbit_autotrader.strategies.legacy_strategy import UpbitStrategyManager


class _DummyLogger:
    def info(self, *_args, **_kwargs):
        return None

    def warning(self, *_args, **_kwargs):
        return None

    def error(self, *_args, **_kwargs):
        return None


class _Spin:
    def __init__(self, value):
        self._value = value

    def value(self):
        return self._value


def test_trading_controller_pyupbit_monkeypatch_path_still_effective():
    class _Trader(TraderTradingController):
        def __init__(self):
            self.spin_k = _Spin(0.5)
            self.logger = _DummyLogger()

    df = pd.DataFrame(
        [
            {"open": 100.0, "high": 130.0, "low": 90.0},
            {"open": 110.0, "high": 140.0, "low": 100.0},
        ]
    )
    trader = _Trader()
    with patch(
        "upbit_autotrader.controllers.trading_controller.pyupbit.get_ohlcv",
        return_value=df,
    ) as mock_ohlcv:
        target = trader.calculate_target_price("KRW-BTC", "minute60")
    assert mock_ohlcv.called
    assert float(target) == 110.0 + ((130.0 - 90.0) * 0.5)


def test_legacy_strategy_pyupbit_monkeypatch_path_still_effective():
    class _Trader:
        def log(self, *_args, **_kwargs):
            return None

    manager = UpbitStrategyManager(_Trader())
    df = pd.DataFrame({"close": [10.0, 11.0, 12.0, 13.0]})
    with patch(
        "upbit_autotrader.strategies.legacy_strategy.pyupbit.get_ohlcv",
        return_value=df,
    ) as mock_ohlcv:
        ma = manager.calculate_ma("KRW-BTC", "minute60", period=3)
    assert mock_ohlcv.called
    assert float(ma) == 12.0


def test_trading_start_wrapper_uses_module_qmessagebox_path():
    class _Trader(TraderTradingController):
        def __init__(self):
            self.upbit = None
            self.is_connected = False

        def _is_paper_mode(self):
            return False

        def _allow_paper_without_login(self):
            return False

    trader = _Trader()
    with patch("upbit_autotrader.controllers.trading_controller.QMessageBox.warning") as mock_warning:
        trader.start_trading()
    mock_warning.assert_called_once()
