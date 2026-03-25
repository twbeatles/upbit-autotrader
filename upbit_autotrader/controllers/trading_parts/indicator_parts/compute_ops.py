from __future__ import annotations

from typing import Any, cast


Config = cast(Any, None)
pd = cast(Any, None)
pyupbit = cast(Any, None)


def bind_runtime(**kwargs):
    globals().update(kwargs)


def calculate_target_price(self, ticker, interval):
    """변동성 돌파 목표가 계산"""
    try:
        df = pyupbit.get_ohlcv(ticker, interval=interval, count=2)
        if df is None or len(df) < 2:
            return None

        prev_high = df.iloc[-2]["high"]
        prev_low = df.iloc[-2]["low"]
        volatility = prev_high - prev_low

        current_open = df.iloc[-1]["open"]
        k = self.spin_k.value()

        return current_open + (volatility * k)
    except Exception as e:
        self.logger.error(f"목표가 계산 실패 ({ticker}): {e}")
        return None


def calculate_ma(self, ticker, interval, period=5):
    """이동평균 계산"""
    try:
        df = pyupbit.get_ohlcv(ticker, interval=interval, count=period + 1)
        if df is None or len(df) < period:
            return None
        return df["close"].rolling(window=period).mean().iloc[-1]
    except Exception as e:
        self.logger.error(f"MA 계산 실패 ({ticker}): {e}")
        return None


def calculate_atr(self, ticker, period=14):
    """ATR (Average True Range) 계산"""
    try:
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        df = pyupbit.get_ohlcv(ticker, interval=interval, count=period + 5)
        if df is None or len(df) < period:
            return None

        high = df["high"]
        low = df["low"]
        close = df["close"]

        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()

        df["tr"] = tr1
        df.loc[tr2 > df["tr"], "tr"] = tr2
        df.loc[tr3 > df["tr"], "tr"] = tr3

        return df["tr"].rolling(window=period).mean().iloc[-1]
    except Exception as e:
        self.logger.error(f"ATR 계산 실패 ({ticker}): {e}")
        return None


def calculate_stoch_rsi(self, ticker, rsi_period=14, stoch_period=14, k_period=3, d_period=3):
    """스토캐스틱 RSI 계산"""
    try:
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        df = pyupbit.get_ohlcv(ticker, interval=interval, count=rsi_period + stoch_period + 10)
        if df is None or len(df) < rsi_period + stoch_period:
            return 50, 50

        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(window=rsi_period).mean()
        avg_loss = loss.rolling(window=rsi_period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        rsi_min = rsi.rolling(window=stoch_period).min()
        rsi_max = rsi.rolling(window=stoch_period).max()
        stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min) * 100

        k = stoch_rsi.rolling(window=k_period).mean().iloc[-1]
        d = stoch_rsi.rolling(window=d_period).mean().iloc[-1]
        return k if not pd.isna(k) else 50, d if not pd.isna(d) else 50
    except Exception as e:
        self.logger.error(f"스토캐스틱 RSI 계산 실패 ({ticker}): {e}")
        return 50, 50


def calculate_dmi_adx(self, ticker, period=14):
    """DMI와 ADX 계산"""
    try:
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        df = pyupbit.get_ohlcv(ticker, interval=interval, count=period * 3)
        if df is None or len(df) < period * 2:
            return 0, 0, 0

        high = df["high"]
        low = df["low"]
        close = df["close"]

        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        plus_dm[(plus_dm < minus_dm) | (plus_dm < 0)] = 0
        minus_dm[(minus_dm < plus_dm) | (minus_dm < 0)] = 0

        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        atr_safe = atr.replace(0, float("nan"))
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr_safe)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr_safe)
        di_sum = plus_di + minus_di
        di_sum_safe = di_sum.replace(0, float("nan"))
        dx = 100 * (abs(plus_di - minus_di) / di_sum_safe)
        adx = dx.rolling(window=period).mean()

        plus_di_val = plus_di.iloc[-1]
        minus_di_val = minus_di.iloc[-1]
        adx_val = adx.iloc[-1]
        return (
            0 if pd.isna(plus_di_val) else plus_di_val,
            0 if pd.isna(minus_di_val) else minus_di_val,
            0 if pd.isna(adx_val) else adx_val,
        )
    except Exception as e:
        self.logger.error(f"DMI/ADX 계산 실패 ({ticker}): {e}")
        return 0, 0, 0


def _compute_rsi_from_close(close, period):
    if close is None or len(close) < period + 1:
        return 50
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean().iloc[-1]
    avg_loss = loss.rolling(window=period).mean().iloc[-1]
    if pd is not None and pd.isna(avg_gain):
        return 50
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi)
