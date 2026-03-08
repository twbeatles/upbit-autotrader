from __future__ import annotations

# Runtime bindings injected by trading_controller facade
Config = None
pd = None
pyupbit = None
time = None


def bind_runtime(**kwargs):
    globals().update(kwargs)



def calculate_target_price(self, ticker, interval):
    """변동성 돌파 목표가 계산"""
    try:
        df = pyupbit.get_ohlcv(ticker, interval=interval, count=2)
        if df is None or len(df) < 2:
            return None
        
        prev_high = df.iloc[-2]['high']
        prev_low = df.iloc[-2]['low']
        volatility = prev_high - prev_low
        
        current_open = df.iloc[-1]['open']
        k = self.spin_k.value()
        
        return current_open + (volatility * k)
    except Exception as e:
        self.logger.error(f"목표가 계산 실패 ({ticker}): {e}")
        return None


def calculate_ma(self, ticker, interval, period=5):
    """이동평균 계산"""
    try:
        df = pyupbit.get_ohlcv(ticker, interval=interval, count=period+1)
        if df is None or len(df) < period:
            return None
        return df['close'].rolling(window=period).mean().iloc[-1]
    except Exception as e:
        self.logger.error(f"MA 계산 실패 ({ticker}): {e}")
        return None


def calculate_rsi(self, ticker, period=14):
    """RSI ??"""
    try:
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        snapshot = self._get_indicator_snapshot(ticker, interval, rsi_period=period)
        if not snapshot:
            return 50
        return snapshot.get('rsi', 50)
    except Exception:
        return 50


def calculate_macd(self, ticker):
    """MACD ?? (MACD, Signal, Histogram ??)"""
    try:
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        snapshot = self._get_indicator_snapshot(ticker, interval)
        if not snapshot:
            return 0, 0, 0
        return (
            snapshot.get('macd', 0),
            snapshot.get('signal', 0),
            snapshot.get('histogram', 0),
        )
    except Exception as e:
        self.logger.error(f"MACD ?? ?? ({ticker}): {e}")
        return 0, 0, 0


def calculate_bollinger_bands(self, ticker):
    """??? ?? ?? (??, ??, ?? ??)"""
    try:
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        snapshot = self._get_indicator_snapshot(ticker, interval)
        if not snapshot:
            return None, None, None
        return (
            snapshot.get('bb_upper'),
            snapshot.get('bb_middle'),
            snapshot.get('bb_lower'),
        )
    except Exception as e:
        self.logger.error(f"??? ?? ?? ?? ({ticker}): {e}")
        return None, None, None


def calculate_atr(self, ticker, period=14):
    """ATR (Average True Range) 계산"""
    try:
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        df = pyupbit.get_ohlcv(ticker, interval=interval, count=period + 5)
        if df is None or len(df) < period:
            return None
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        # True Range 계산 (DataFrame 내장 연산 사용)
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        
        # 각 행에서 최대값 선택
        df['tr'] = tr1
        df.loc[tr2 > df['tr'], 'tr'] = tr2
        df.loc[tr3 > df['tr'], 'tr'] = tr3
        
        # ATR = True Range의 이동평균
        atr = df['tr'].rolling(window=period).mean().iloc[-1]
        return atr
    except Exception as e:
        self.logger.error(f"ATR 계산 실패 ({ticker}): {e}")
        return None


def calculate_volume_avg(self, ticker, period=20):
    """?? ??? ??"""
    try:
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        snapshot = self._get_indicator_snapshot(ticker, interval, volume_period=period)
        if not snapshot:
            return None, None
        return snapshot.get('current_volume'), snapshot.get('avg_volume')
    except Exception:
        return None, None


def calculate_stoch_rsi(self, ticker, rsi_period=14, stoch_period=14, k_period=3, d_period=3):
    """스토캐스틱 RSI 계산 (v2.5 신규)"""
    try:
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        df = pyupbit.get_ohlcv(ticker, interval=interval, count=rsi_period + stoch_period + 10)
        if df is None or len(df) < rsi_period + stoch_period:
            return 50, 50  # 기본값
        
        # RSI 계산
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(window=rsi_period).mean()
        avg_loss = loss.rolling(window=rsi_period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # 스토캐스틱 RSI 계산
        rsi_min = rsi.rolling(window=stoch_period).min()
        rsi_max = rsi.rolling(window=stoch_period).max()
        stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min) * 100
        
        # %K, %D
        k = stoch_rsi.rolling(window=k_period).mean().iloc[-1]
        d = stoch_rsi.rolling(window=d_period).mean().iloc[-1]
        
        return k if not pd.isna(k) else 50, d if not pd.isna(d) else 50
    except Exception as e:
        self.logger.error(f"스토캐스틱 RSI 계산 실패 ({ticker}): {e}")
        return 50, 50


def calculate_dmi_adx(self, ticker, period=14):
    """DMI와 ADX 계산 (v2.7) - 추세 강도 측정"""
    try:
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        df = pyupbit.get_ohlcv(ticker, interval=interval, count=period * 3)
        if df is None or len(df) < period * 2:
            return 0, 0, 0  # +DI, -DI, ADX
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        # +DM, -DM 계산
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        # 조건: +DM > -DM일 때만 +DM 유효
        plus_dm[(plus_dm < minus_dm) | (plus_dm < 0)] = 0
        minus_dm[(minus_dm < plus_dm) | (minus_dm < 0)] = 0
        
        # True Range
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 평활화 (Wilder 스무딩)
        atr = tr.rolling(window=period).mean()
        
        # ZeroDivision 방지: ATR이 0인 경우 처리
        atr_safe = atr.replace(0, float('nan'))
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr_safe)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr_safe)
        
        # DX와 ADX - ZeroDivision 방지
        di_sum = plus_di + minus_di
        di_sum_safe = di_sum.replace(0, float('nan'))
        dx = 100 * (abs(plus_di - minus_di) / di_sum_safe)
        adx = dx.rolling(window=period).mean()
        
        # NaN 처리
        plus_di_val = plus_di.iloc[-1]
        minus_di_val = minus_di.iloc[-1]
        adx_val = adx.iloc[-1]
        
        return (
            0 if pd.isna(plus_di_val) else plus_di_val,
            0 if pd.isna(minus_di_val) else minus_di_val,
            0 if pd.isna(adx_val) else adx_val
        )
    except Exception as e:
        self.logger.error(f"DMI/ADX 계산 실패 ({ticker}): {e}")
        return 0, 0, 0


def _get_indicator_cache_ttl(self, interval):
    self._ensure_indicator_cache_state()
    return float(self._indicator_cache_ttl_sec.get(interval, 5))


def _compute_rsi_from_close(self, close, period):
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


def _get_indicator_snapshot(self, ticker, interval, rsi_period=None, volume_period=None, bb_period=None):
    if pyupbit is None or pd is None:
        return None
    self._ensure_indicator_cache_state()
    if rsi_period is None:
        rsi_period = self.spin_rsi_period.value() if hasattr(self, "spin_rsi_period") else Config.DEFAULT_RSI_PERIOD
    rsi_period = int(rsi_period)
    volume_period = int(volume_period or Config.DEFAULT_VOLUME_PERIOD)
    bb_period = int(bb_period or Config.DEFAULT_BB_PERIOD)
    cache_key = (ticker, interval, rsi_period, volume_period, bb_period)
    now_ts = time.time()
    ttl = self._get_indicator_cache_ttl(interval)
    cached = self._indicator_cache.get(cache_key)
    if cached and (now_ts - cached.get('ts', 0)) < ttl:
        return cached.get('data')
    count = max(50, rsi_period + 2, volume_period + 1, bb_period + 5)
    df = pyupbit.get_ohlcv(ticker, interval=interval, count=count)
    if df is None or len(df) == 0:
        return None
    close = df['close']
    rsi = self._compute_rsi_from_close(close, rsi_period)
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
        current_volume = float(df.iloc[-1]['volume'])
        prev_volumes = df['volume'].iloc[-(volume_period + 1):-1]
        if len(prev_volumes) > 0:
            avg_volume = float(prev_volumes.mean())
        else:
            avg_volume = float(df['volume'].iloc[:-1].mean()) if len(df) > 1 else 0.0
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
        'rsi': rsi,
        'macd': macd,
        'signal': signal,
        'histogram': histogram,
        'current_volume': current_volume,
        'avg_volume': avg_volume,
        'bb_upper': bb_upper,
        'bb_middle': bb_middle,
        'bb_lower': bb_lower,
        'ema_fast': ema_fast,
        'ema_slow': ema_slow,
        'ema_fast_prev': ema_fast_prev,
        'donchian_upper': donchian_upper,
        'donchian_lower': donchian_lower,
        'zscore': zscore,
        'adx': adx,
        'realized_vol_pct': realized_vol_pct,
        'ts_momentum_pct': ts_momentum_pct,
    }
    self._indicator_cache[cache_key] = {'ts': now_ts, 'data': snapshot}
    if len(self._indicator_cache) > 1024:
        oldest_key = min(self._indicator_cache, key=lambda k: self._indicator_cache[k].get('ts', 0))
        self._indicator_cache.pop(oldest_key, None)
    return snapshot
