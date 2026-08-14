from __future__ import annotations

from typing import Any, cast

from . import cache_ops, compute_ops


Config = cast(Any, None)
pd = cast(Any, None)
pyupbit = cast(Any, None)
time = cast(Any, None)


def bind_runtime(**kwargs):
    globals().update(kwargs)
    cache_ops.bind_runtime(**kwargs)
    compute_ops.bind_runtime(**kwargs)


def calculate_rsi(self, ticker, period=14):
    """RSI 계산"""
    try:
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        snapshot = _get_indicator_snapshot(self, ticker, interval, rsi_period=period)
        if not snapshot:
            return 50
        return snapshot.get("rsi", 50)
    except Exception:
        return 50


def calculate_macd(self, ticker):
    """MACD 계산"""
    try:
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        snapshot = _get_indicator_snapshot(self, ticker, interval)
        if not snapshot:
            return 0, 0, 0
        return (
            snapshot.get("macd", 0),
            snapshot.get("signal", 0),
            snapshot.get("histogram", 0),
        )
    except Exception as e:
        self.logger.error(f"MACD 계산 실패 ({ticker}): {e}")
        return 0, 0, 0


def calculate_bollinger_bands(self, ticker):
    """볼린저 밴드 계산"""
    try:
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        snapshot = _get_indicator_snapshot(self, ticker, interval)
        if not snapshot:
            return None, None, None
        return (
            snapshot.get("bb_upper"),
            snapshot.get("bb_middle"),
            snapshot.get("bb_lower"),
        )
    except Exception as e:
        self.logger.error(f"볼린저 밴드 계산 실패 ({ticker}): {e}")
        return None, None, None


def calculate_volume_avg(self, ticker, period=20):
    """거래량 평균 계산"""
    try:
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        snapshot = _get_indicator_snapshot(self, ticker, interval, volume_period=period)
        if not snapshot:
            return None, None
        return snapshot.get("current_volume"), snapshot.get("avg_volume")
    except Exception:
        return None, None


def _get_indicator_snapshot(self, ticker, interval, rsi_period=None, volume_period=None, bb_period=None):
    if pyupbit is None or pd is None:
        return None
    self._ensure_indicator_cache_state()
    if rsi_period is None:
        if hasattr(self, "spin_rsi_period"):
            rsi_period = self.spin_rsi_period.value()
        else:
            rsi_period = Config.DEFAULT_RSI_PERIOD
    rsi_period = int(rsi_period)
    volume_period = int(volume_period or Config.DEFAULT_VOLUME_PERIOD)
    bb_period = int(bb_period or Config.DEFAULT_BB_PERIOD)
    cache_key = cache_ops._build_snapshot_cache_key(ticker, interval, rsi_period, volume_period, bb_period)
    now_ts = time.time()
    ttl = cache_ops._get_indicator_cache_ttl(self, interval)
    cached = self._indicator_cache.get(cache_key)
    if cached and (now_ts - cached.get("ts", 0)) < ttl:
        return cached.get("data")

    count = max(50, rsi_period + 2, volume_period + 1, bb_period + 5)
    df = compute_ops._fetch_ohlcv(self, ticker, interval=interval, count=count)
    if df is None or len(df) == 0:
        return None

    close = df["close"]
    rsi = compute_ops._compute_rsi_from_close(close, rsi_period)
    macd = signal = histogram = 0.0
    if len(close) >= 30:
        ema_fast = close.ewm(span=Config.DEFAULT_MACD_FAST, adjust=False).mean()
        ema_slow = close.ewm(span=Config.DEFAULT_MACD_SLOW, adjust=False).mean()
        macd_series = ema_fast - ema_slow
        signal_series = macd_series.ewm(span=Config.DEFAULT_MACD_SIGNAL, adjust=False).mean()
        hist_series = macd_series - signal_series
        macd = float(macd_series.iloc[-1])
        signal = float(signal_series.iloc[-1])
        histogram = float(hist_series.iloc[-1])

    current_volume = None
    avg_volume = None
    if len(df) >= volume_period:
        current_volume = float(df.iloc[-1]["volume"])
        prev_volumes = df["volume"].iloc[-(volume_period + 1):-1]
        if len(prev_volumes) > 0:
            avg_volume = float(prev_volumes.mean())
        else:
            avg_volume = float(df["volume"].iloc[:-1].mean()) if len(df) > 1 else 0.0

    bb_upper = bb_middle = bb_lower = None
    if len(df) >= bb_period:
        bb_middle = float(close.rolling(window=bb_period).mean().iloc[-1])
        bb_std = float(close.rolling(window=bb_period).std().iloc[-1])
        bb_upper = bb_middle + (bb_std * Config.DEFAULT_BB_STD)
        bb_lower = bb_middle - (bb_std * Config.DEFAULT_BB_STD)

    ema_fast = ema_slow = ema_fast_prev = 0.0
    if len(close) >= 30:
        ema_fast_series = close.ewm(span=12, adjust=False).mean()
        ema_slow_series = close.ewm(span=26, adjust=False).mean()
        ema_fast = float(ema_fast_series.iloc[-1])
        ema_slow = float(ema_slow_series.iloc[-1])
        ema_fast_prev = float(ema_fast_series.iloc[-2]) if len(ema_fast_series) >= 2 else ema_fast

    donchian_upper = donchian_lower = None
    if len(df) >= 21:
        donchian_upper = float(df["high"].iloc[-21:-1].max())
        donchian_lower = float(df["low"].iloc[-21:-1].min())

    zscore = 0.0
    if len(close) >= 21:
        rolling_mean = close.rolling(window=20).mean().iloc[-1]
        rolling_std = close.rolling(window=20).std().iloc[-1]
        if rolling_std and rolling_std > 0:
            zscore = float((close.iloc[-1] - rolling_mean) / rolling_std)

    ts_momentum_pct = 0.0
    if len(close) >= 21:
        base = float(close.iloc[-21])
        if base > 0:
            ts_momentum_pct = float((close.iloc[-1] - base) / base * 100.0)

    realized_vol_pct = 0.0
    if len(close) >= 21:
        ret = close.pct_change().dropna()
        if len(ret) >= 20:
            realized_vol_pct = float(ret.iloc[-20:].std() * (20 ** 0.5) * 100.0)

    adx = 0.0
    if len(df) >= 30:
        high = df["high"]
        low = df["low"]
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[(plus_dm < 0) | (plus_dm < minus_dm)] = 0
        minus_dm[(minus_dm < 0) | (minus_dm < plus_dm)] = 0
        period = 14
        atr = tr.rolling(window=period).mean().replace(0, float("nan"))
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        di_sum = (plus_di + minus_di).replace(0, float("nan"))
        dx = 100 * (plus_di - minus_di).abs() / di_sum
        adx_val = dx.rolling(window=period).mean().iloc[-1]
        if not pd.isna(adx_val):
            adx = float(adx_val)

    snapshot = {
        "rsi": rsi,
        "macd": macd,
        "signal": signal,
        "histogram": histogram,
        "current_volume": current_volume,
        "avg_volume": avg_volume,
        "bb_upper": bb_upper,
        "bb_middle": bb_middle,
        "bb_lower": bb_lower,
        "ema_fast": ema_fast,
        "ema_slow": ema_slow,
        "ema_fast_prev": ema_fast_prev,
        "donchian_upper": donchian_upper,
        "donchian_lower": donchian_lower,
        "zscore": zscore,
        "adx": adx,
        "realized_vol_pct": realized_vol_pct,
        "ts_momentum_pct": ts_momentum_pct,
    }
    self._indicator_cache[cache_key] = {"ts": now_ts, "data": snapshot}
    cache_ops._prune_indicator_cache(self._indicator_cache)
    return snapshot
