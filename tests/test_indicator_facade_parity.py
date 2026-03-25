import types

import pandas as pd

from upbit_autotrader.controllers.trading_parts import indicator_ops
from upbit_autotrader.core.config import Config


class _Logger:
    def error(self, *_args, **_kwargs):
        return None


class _Spin:
    def __init__(self, value):
        self._value = value

    def value(self):
        return self._value


class _Combo:
    def __init__(self, text):
        self._text = text

    def currentText(self):
        return self._text


class _DummyTrader:
    def __init__(self):
        self.spin_k = _Spin(0.5)
        self.spin_rsi_period = _Spin(Config.DEFAULT_RSI_PERIOD)
        self.combo_candle = _Combo(Config.DEFAULT_CANDLE)
        self.logger = _Logger()

    def _ensure_indicator_cache_state(self):
        if not hasattr(self, "_indicator_cache"):
            self._indicator_cache = {}
        if not hasattr(self, "_indicator_cache_ttl_sec"):
            self._indicator_cache_ttl_sec = dict(getattr(Config, "INDICATOR_CACHE_TTL_BY_INTERVAL", {}))


def _make_df():
    rows = 40
    base = [100 + idx for idx in range(rows)]
    return pd.DataFrame(
        {
            "open": base,
            "high": [v + 2 for v in base],
            "low": [v - 2 for v in base],
            "close": [v + 1 for v in base],
            "volume": [1000 + idx * 10 for idx in range(rows)],
        }
    )


def test_indicator_facade_preserves_snapshot_shape():
    trader = _DummyTrader()
    fake_pyupbit = types.SimpleNamespace(get_ohlcv=lambda *_args, **_kwargs: _make_df())
    indicator_ops.bind_runtime(Config=Config, pd=pd, pyupbit=fake_pyupbit, time=types.SimpleNamespace(time=lambda: 1000.0))

    target_price = indicator_ops.calculate_target_price(trader, "KRW-BTC", "minute240")
    rsi = indicator_ops.calculate_rsi(trader, "KRW-BTC", period=14)
    snapshot = indicator_ops._get_indicator_snapshot(trader, "KRW-BTC", "minute240")

    assert target_price is not None
    assert isinstance(rsi, (int, float))
    assert isinstance(snapshot, dict)
    for key in (
        "rsi",
        "macd",
        "signal",
        "histogram",
        "current_volume",
        "avg_volume",
        "bb_upper",
        "bb_middle",
        "bb_lower",
        "adx",
        "realized_vol_pct",
        "ts_momentum_pct",
    ):
        assert key in snapshot


def test_indicator_facade_uses_cache_for_repeated_snapshot_calls():
    trader = _DummyTrader()
    call_state = {"count": 0}

    def _get_ohlcv(*_args, **_kwargs):
        call_state["count"] += 1
        return _make_df()

    fake_pyupbit = types.SimpleNamespace(get_ohlcv=_get_ohlcv)
    fake_time = types.SimpleNamespace(time=lambda: 1000.0)
    indicator_ops.bind_runtime(Config=Config, pd=pd, pyupbit=fake_pyupbit, time=fake_time)

    first = indicator_ops._get_indicator_snapshot(trader, "KRW-BTC", "minute240")
    second = indicator_ops._get_indicator_snapshot(trader, "KRW-BTC", "minute240")

    assert first == second
    assert call_state["count"] == 1
