import datetime
import time

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTableWidgetItem, QMessageBox

from upbit_config import Config
from upbit_entry_filter import should_enter_by_score

try:
    import pandas as pd
    import pyupbit
except ImportError:
    pd = None
    pyupbit = None


class TraderTradingController:
    def login(self):
        """업비트 API 연결"""
        access = self.input_access.text().strip()
        secret = self.input_secret.text().strip()
        
        if not access or not secret:
            QMessageBox.warning(self, "경고", "API Access Key와 Secret Key를 입력해주세요.")
            return
        
        self.log("🔄 업비트 API 연결 시도 중...")
        self.lbl_connection.setText("● 연결 중...")
        self.lbl_connection.setStyleSheet("color: #ffc107; font-weight: bold;")
        
        try:
            self.upbit = pyupbit.Upbit(access, secret)
            balance = self.upbit.get_balance("KRW")
            
            if balance is not None:
                self.is_connected = True
                self.balance = balance
                self.initial_balance = balance
                
                self.lbl_balance.setText(f"💰 주문가능금액: {balance:,.0f} 원")
                self.lbl_connection.setText("● 연결됨")
                self.lbl_connection.setStyleSheet("color: #00b894; font-weight: bold;")
                self.btn_start.setEnabled(True)
                self.btn_batch_sell.setEnabled(True)
                self.btn_batch_buy.setEnabled(True)
                
                self.log(f"✅ 업비트 API 연결 성공 (잔고: {balance:,.0f}원)")
                self.logger.info(f"API 연결 성공, 잔고: {balance:,.0f}원")
            else:
                raise Exception("잔고 조회 실패")
                
        except Exception as e:
            self.is_connected = False
            self.lbl_connection.setText("● 연결 실패")
            self.lbl_connection.setStyleSheet("color: #e63946; font-weight: bold;")
            self.log(f"❌ API 연결 실패: {e}")
            self.logger.error(f"API 연결 실패: {e}")
            QMessageBox.critical(self, "오류", f"API 연결에 실패했습니다.\n{e}")

    def get_balance(self):
        """잔고 조회"""
        if not self.upbit:
            return
        try:
            balance = self.upbit.get_balance("KRW")
            if balance is None:
                self.logger.warning("잔고 조회 결과가 None입니다.")
                return
            self.balance = float(balance)
            self.lbl_balance.setText(f"💰 주문가능금액: {self.balance:,.0f} 원")
        except Exception as e:
            self.logger.error(f"잔고 조회 실패: {e}")

    # ------------------------------------------------------------------
    # 매매 시작/중지
    # ------------------------------------------------------------------

    def start_trading(self):
        """매매 시작"""
        if not self.upbit or not self.is_connected:
            QMessageBox.warning(self, "경고", "먼저 업비트 API에 연결해주세요.")
            return

        coins_text = self.input_coins.text().replace(" ", "")
        coins = [c for c in coins_text.split(',') if c]
        
        if not coins:
            QMessageBox.warning(self, "경고", "감시할 코인을 입력해주세요.")
            return
        
        # 코인 코드 검증
        invalid_coins = [c for c in coins if not c.startswith("KRW-")]
        if invalid_coins:
            QMessageBox.warning(self, "경고", 
                f"잘못된 코인 코드: {', '.join(invalid_coins)}\n코인 코드는 'KRW-' 형식이어야 합니다.")
            return
        
        self.universe = {}
        self.table.setRowCount(0)
        self.is_running = True
        self.daily_loss_triggered = False
        self._ensure_order_stability_state()
        self._next_trading_session()
        self._reconcile_pending_orders(force=False)
        self._ensure_indicator_cache_state()
        self._indicator_cache.clear()
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_trading.setText("● 분석 중")
        self.status_trading.setStyleSheet("color: #00b4d8;")
        
        candle_interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        self.table.setUpdatesEnabled(False)
        try:
            for coin in coins:
                try:
                    # 목표가 및 MA 계산
                    if self.strategy:
                        target_price = self.strategy.calculate_target_price(coin, candle_interval)
                    else:
                        target_price = self.calculate_target_price(coin, candle_interval)
                    ma5 = self.calculate_ma(coin, candle_interval, 5)
                    current_price = pyupbit.get_current_price(coin)

                    if target_price is None or ma5 is None:
                        self.log(f"[WARN] {coin} 데이터 조회 실패")
                        continue

                    self.universe[coin] = {
                        'name': coin,
                        'state': '감시중',
                        'row': len(self.universe),
                        'target': target_price,
                        'ma5': ma5,
                        'current': current_price or 0,
                        'qty': 0,
                        'buy_price': 0,
                        'invest_amt': 0,
                        'high_since_buy': 0,
                        'max_profit_rate': 0.0
                    }

                    row = self.universe[coin]['row']
                    self.table.insertRow(row)
                    self.table.setItem(row, 0, QTableWidgetItem(coin))
                    self.table.setItem(row, 1, QTableWidgetItem(f"{current_price:,.0f}" if current_price else "-"))
                    self.table.setItem(row, 2, QTableWidgetItem(f"{target_price:,.0f}"))
                    self.table.setItem(row, 3, QTableWidgetItem(f"{ma5:,.0f}"))
                    self.set_table_item(row, 4, "👀 감시중", "#00b894")
                    self.universe[coin]['ui_items'] = {
                        'price': self.table.item(row, 1),
                        'state': self.table.item(row, 4),
                        'qty': self.table.item(row, 5),
                        'buy_price': self.table.item(row, 6),
                        'profit': self.table.item(row, 7),
                        'max_profit': self.table.item(row, 8),
                        'invest': self.table.item(row, 9),
                    }

                    self.log(f"[{coin}] 목표가:{target_price:,.0f}, MA5:{ma5:,.0f}")

                except Exception as e:
                    self.log(f"[ERROR] {coin} 초기화 실패: {e}")
                    self.logger.error(f"{coin} 초기화 실패: {e}")
        finally:
            self.table.setUpdatesEnabled(True)
        if self.universe:
            # 가격 모니터링 시작
            if hasattr(self, "_restart_price_thread"):
                self._restart_price_thread(list(self.universe.keys()))
            else:
                self.price_thread.set_coins(list(self.universe.keys()))
                if not self.price_thread.isRunning():
                    self.price_thread.start()
            
            self.status_trading.setText("● 매매 중")
            self.status_trading.setStyleSheet("color: #00b894;")
            self.status_realtime.setText(f"실시간: {len(self.universe)}종목 감시")
            
            self.log(f"🚀 자동매매 시작 (총 {len(self.universe)} 코인)")
            self.logger.info(f"매매 시작: {len(self.universe)} 코인")
        else:
            self.stop_trading()
            QMessageBox.warning(self, "경고", "유효한 코인이 없습니다.")

    def stop_trading(self):
        """매매 중지"""
        self.is_running = False
        self.price_thread.stop()
        self.price_thread.wait(2000)
        self._reconcile_pending_orders(force=True)
        
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_trading.setText("● 중지됨")
        self.status_trading.setStyleSheet("color: #e63946;")
        self.status_realtime.setText("실시간: 비활성")
        
        self.log("⏹️ 매매가 중지되었습니다")
        self.logger.info("매매 중지")

    # ------------------------------------------------------------------
    # 전략 계산
    # ------------------------------------------------------------------

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

    def _ensure_indicator_cache_state(self):
        if not hasattr(self, '_indicator_cache'):
            self._indicator_cache = {}
        if not hasattr(self, '_indicator_cache_ttl_sec'):
            self._indicator_cache_ttl_sec = dict(getattr(Config, 'INDICATOR_CACHE_TTL_BY_INTERVAL', {}))
    def _ensure_order_stability_state(self):
        if not hasattr(self, "_reserved_krw_by_ticker"):
            self._reserved_krw_by_ticker = {}
        if not hasattr(self, "_active_session_id"):
            self._active_session_id = 0
        if not hasattr(self, "_order_error_log_ts"):
            self._order_error_log_ts = {}
    def _next_trading_session(self):
        self._ensure_order_stability_state()
        self._active_session_id += 1
        return self._active_session_id
    def _get_reserved_krw_total(self):
        self._ensure_order_stability_state()
        return sum(max(0.0, float(v or 0.0)) for v in self._reserved_krw_by_ticker.values())
    def _get_available_krw(self):
        balance = float(getattr(self, "balance", 0) or 0)
        return max(0.0, balance - self._get_reserved_krw_total())
    def _reserve_krw_for_buy(self, ticker, amount, session_id=0):
        self._ensure_order_stability_state()
        amount = float(amount or 0.0)
        if amount <= 0:
            return False
        existing = float(self._reserved_krw_by_ticker.get(ticker, 0.0) or 0.0)
        available = self._get_available_krw() + existing
        if amount > (available + 1e-8):
            return False
        self._reserved_krw_by_ticker[ticker] = amount
        return True
    def _release_reserved_krw(self, ticker):
        self._ensure_order_stability_state()
        return float(self._reserved_krw_by_ticker.pop(ticker, 0.0) or 0.0)
    def _sync_reserved_with_pending(self):
        self._ensure_order_stability_state()
        if not hasattr(self, "order_service"):
            self._reserved_krw_by_ticker.clear()
            return
        if hasattr(self.order_service, "list_pending"):
            pending_tickers = set(self.order_service.list_pending().keys())
        else:
            pending_tickers = set(getattr(self, "pending_orders", {}).keys())
        for ticker in list(self._reserved_krw_by_ticker.keys()):
            if ticker not in pending_tickers:
                self._reserved_krw_by_ticker.pop(ticker, None)
    def _safe_log_order_error(self, uuid, message):
        self._ensure_order_stability_state()
        now_ts = time.time()
        key = str(uuid)
        last_ts = float(self._order_error_log_ts.get(key, 0.0) or 0.0)
        if (now_ts - last_ts) < 5.0:
            return
        self._order_error_log_ts[key] = now_ts
        if hasattr(self, "logger"):
            self.logger.warning(message)
    def _safe_get_order(self, uuid):
        if not getattr(self, "upbit", None) or not uuid:
            return None
        delays = tuple(getattr(Config, "ORDER_STATUS_RETRY_DELAYS_SEC", (0.3, 0.6, 1.2)))
        if not delays:
            delays = (0.0,)
        last_error = None
        for idx, delay in enumerate(delays):
            try:
                return self.upbit.get_order(uuid)
            except Exception as e:
                last_error = e
                self._safe_log_order_error(uuid, f"주문 상태 조회 실패 ({uuid}): {e}")
                if idx < len(delays) - 1 and delay > 0:
                    time.sleep(delay)
        if last_error is not None and hasattr(self, "logger"):
            self.logger.error(f"주문 상태 조회 최종 실패 ({uuid}): {last_error}")
        return None
    def _reconcile_pending_orders(self, force=False):
        self._ensure_order_stability_state()
        if not getattr(self, "upbit", None) or not hasattr(self, "order_service"):
            return
        now = datetime.datetime.now()
        stale_timeout = float(getattr(Config, "PENDING_STALE_TIMEOUT_SEC", 90))
        if hasattr(self.order_service, "list_pending"):
            pending_items = self.order_service.list_pending().items()
        else:
            pending_items = getattr(self, "pending_orders", {}).items()
        for ticker, pending in list(pending_items):
            uuid = pending.get("uuid")
            requested_at = pending.get("requested_at")
            if not isinstance(requested_at, datetime.datetime):
                requested_at = now
            order = self._safe_get_order(uuid)
            age_sec = max(0.0, (now - requested_at).total_seconds())
            if not order:
                if force and age_sec >= stale_timeout:
                    if self.order_service.clear_pending_if_uuid(ticker, uuid):
                        self._release_reserved_krw(ticker)
                        if hasattr(self, "log"):
                            self.log(f"⚠️ [{ticker}] 대기 주문 로컬 정리(시간초과)")
                continue
            state = str(order.get("state", "")).lower()
            prev_retry = int(pending.get("retry_count", 0) or 0)
            self.order_service.update_pending(
                ticker,
                last_checked_at=now,
                retry_count=prev_retry + 1,
            )
            if state in ("done", "cancel"):
                if self.order_service.clear_pending_if_uuid(ticker, uuid):
                    self._release_reserved_krw(ticker)
            elif force and age_sec >= stale_timeout:
                if self.order_service.clear_pending_if_uuid(ticker, uuid):
                    self._release_reserved_krw(ticker)
                    if hasattr(self, "log"):
                        self.log(f"⚠️ [{ticker}] 장기 대기 주문 로컬 정리")
        self._sync_reserved_with_pending()
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
            avg_volume = float(df['volume'].iloc[:-1].mean())
        bb_upper = bb_middle = bb_lower = None
        if len(df) >= bb_period:
            bb_middle = float(close.rolling(window=bb_period).mean().iloc[-1])
            bb_std = float(close.rolling(window=bb_period).std().iloc[-1])
            bb_upper = bb_middle + (bb_std * Config.DEFAULT_BB_STD)
            bb_lower = bb_middle - (bb_std * Config.DEFAULT_BB_STD)
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
        }
        self._indicator_cache[cache_key] = {'ts': now_ts, 'data': snapshot}
        if len(self._indicator_cache) > 1024:
            oldest_key = min(self._indicator_cache, key=lambda k: self._indicator_cache[k].get('ts', 0))
            self._indicator_cache.pop(oldest_key, None)
        return snapshot
    def api_call_with_retry(self, func, *args, max_retries=None, delay=None):
        """API 호출 재시도 래퍼 (v2.5 신규)"""
        max_retries = max_retries or Config.API_MAX_RETRIES
        delay = delay or Config.API_RETRY_DELAY
        
        for attempt in range(max_retries):
            try:
                result = func(*args)
                return result
            except Exception as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"API 호출 실패 (시도 {attempt + 1}/{max_retries}): {e}")
                    time.sleep(delay * (attempt + 1))
                else:
                    self.logger.error(f"API 호출 최종 실패: {e}")
                    raise

    def calculate_entry_score(self, ticker, curr_price, info, snapshot=None):
        """진입 점수 계산 (v2.5 신규) - 0~100점"""
        score = 0
        reasons = []
        weights = Config.ENTRY_WEIGHTS
        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        if snapshot is None:
            snapshot = self._get_indicator_snapshot(
                ticker,
                interval,
                rsi_period=self.spin_rsi_period.value(),
                volume_period=Config.DEFAULT_VOLUME_PERIOD,
                bb_period=Config.DEFAULT_BB_PERIOD,
            )
        
        # 1. 목표가 돌파 (필수 조건이지만 점수로도 반영)
        if curr_price >= info['target']:
            score += weights['target_break']
            reasons.append(f"+{weights['target_break']} 목표가 돌파")
        
        # 2. MA5 필터
        if curr_price >= info['ma5']:
            score += weights['ma_filter']
            reasons.append(f"+{weights['ma_filter']} MA5 위")
        
        # 3. RSI 최적 구간
        if self.chk_use_rsi.isChecked():
            rsi = snapshot.get("rsi", 50) if snapshot else 50
            if 30 <= rsi <= 70:
                score += weights['rsi_optimal']
                reasons.append(f"+{weights['rsi_optimal']} RSI {rsi:.1f} (최적)")
            elif rsi < 30:
                score += weights['rsi_optimal'] // 2  # 과매도는 절반 점수
                reasons.append(f"+{weights['rsi_optimal']//2} RSI {rsi:.1f} (과매도)")
        else:
            score += weights['rsi_optimal']  # RSI 미사용시 만점
        
        # 4. MACD 골든크로스
        if hasattr(self, 'chk_use_macd') and self.chk_use_macd.isChecked():
            if snapshot:
                macd = snapshot.get("macd", 0)
                signal = snapshot.get("signal", 0)
            else:
                macd, signal, _ = self.calculate_macd(ticker)
            if macd > signal:
                score += weights['macd_golden']
                reasons.append(f"+{weights['macd_golden']} MACD 골든크로스")
        else:
            score += weights['macd_golden']  # MACD 미사용시 만점
        
        # 5. 거래량 확인
        if self.chk_use_volume.isChecked():
            if snapshot:
                curr_vol = snapshot.get("current_volume")
                avg_vol = snapshot.get("avg_volume")
            else:
                curr_vol, avg_vol = self.calculate_volume_avg(ticker, Config.DEFAULT_VOLUME_PERIOD)
            if curr_vol and avg_vol:
                required_vol = avg_vol * self.spin_volume_mult.value()
                if curr_vol >= required_vol:
                    score += weights['volume_confirm']
                    reasons.append(f"+{weights['volume_confirm']} 거래량 충분")
        else:
            score += weights['volume_confirm']
        
        # 6. 볼린저 밴드 포지션
        if snapshot:
            upper = snapshot.get("bb_upper")
            middle = snapshot.get("bb_middle")
            lower = snapshot.get("bb_lower")
        else:
            upper, middle, lower = self.calculate_bollinger_bands(ticker)
        if lower and middle:
            if lower <= curr_price <= middle:  # 하단~중간: 최적
                score += weights['bb_position']
                reasons.append(f"+{weights['bb_position']} BB 최적 구간")
            elif middle < curr_price <= upper:  # 중간~상단: 절반
                score += weights['bb_position'] // 2
                reasons.append(f"+{weights['bb_position']//2} BB 중상단")
        
        return score, reasons

    # ------------------------------------------------------------------
    # 가격 업데이트 및 조건 확인
    # ------------------------------------------------------------------

    def on_price_update(self, prices):
        """실시간 가격 업데이트"""
        if not self.is_running:
            return

        self.table.setUpdatesEnabled(False)
        try:
            for ticker, price in prices.items():
                if ticker not in self.universe:
                    continue

                info = self.universe[ticker]
                info['current'] = price

                if self.strategy:
                    self.strategy.update_recent_price(ticker, price)

                # 현재가 UI 업데이트
                price_item = info.get('ui_items', {}).get('price')
                if price_item is None:
                    price_item = QTableWidgetItem("-")
                    self.table.setItem(info['row'], 1, price_item)
                    info.setdefault('ui_items', {})['price'] = price_item
                price_item.setText(f"{price:,.0f}")

                # 매수 로직
                if info['state'] == '감시중' and info['qty'] == 0:
                    self._check_buy_condition(ticker, price, info)

                # 매도 로직
                elif info['state'] == '보유중' and info['qty'] > 0:
                    self._check_sell_condition(ticker, price, info)
        finally:
            self.table.setUpdatesEnabled(True)

    def _check_buy_condition(self, ticker, curr, info):
        """매수 조건 확인"""
        if self.strategy:
            if not self.strategy.check_cooldown(ticker):
                return
            if not self.strategy.check_mtf_condition(ticker):
                return

        # 1. 목표가 돌파
        if curr < info['target']:
            return
        
        # 2. MA5 위
        if curr < info['ma5']:
            return

        if self.strategy and hasattr(self, 'chk_use_breakout_confirm') and self.chk_use_breakout_confirm.isChecked():
            confirm_ticks = self.spin_breakout_ticks.value() if hasattr(self, 'spin_breakout_ticks') else None
            if not self.strategy.check_breakout_confirmation(ticker, info['target'], confirm_ticks):
                return

        interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        need_snapshot = (
            self.chk_use_rsi.isChecked()
            or (hasattr(self, 'chk_use_macd') and self.chk_use_macd.isChecked())
            or self.chk_use_volume.isChecked()
            or self.chk_use_entry_scoring.isChecked()
        )
        snapshot = None
        if need_snapshot:
            snapshot = self._get_indicator_snapshot(
                ticker,
                interval,
                rsi_period=self.spin_rsi_period.value(),
                volume_period=Config.DEFAULT_VOLUME_PERIOD,
                bb_period=Config.DEFAULT_BB_PERIOD,
            )
        
        # 3. RSI 필터
        if self.chk_use_rsi.isChecked():
            rsi = snapshot.get("rsi", 50) if snapshot else self.calculate_rsi(ticker, self.spin_rsi_period.value())
            if rsi >= self.spin_rsi_upper.value():
                self.log(f"[{ticker}] RSI {rsi:.1f} >= {self.spin_rsi_upper.value()} (과매수) 진입 보류")
                return
        
        # 4. MACD 필터 (골든크로스: MACD > Signal)
        if hasattr(self, 'chk_use_macd') and self.chk_use_macd.isChecked():
            if snapshot:
                macd = snapshot.get("macd", 0)
                signal = snapshot.get("signal", 0)
            else:
                macd, signal, _ = self.calculate_macd(ticker)
            if macd <= signal:
                self.log(f"[{ticker}] MACD {macd:.2f} <= Signal {signal:.2f} (하락세) 진입 보류")
                return
        
        # 5. 거래량 필터
        if self.chk_use_volume.isChecked():
            if snapshot:
                curr_vol = snapshot.get("current_volume")
                avg_vol = snapshot.get("avg_volume")
            else:
                curr_vol, avg_vol = self.calculate_volume_avg(ticker, Config.DEFAULT_VOLUME_PERIOD)
            if curr_vol and avg_vol:
                required_vol = avg_vol * self.spin_volume_mult.value()
                if curr_vol < required_vol:
                    self.log(f"[{ticker}] 거래량 부족 ({curr_vol:,.0f} < {required_vol:,.0f}) 진입 보류")
                    return
        
        # 6. 리스크 관리
        if not self.check_risk_limits():
            return
        
        # 7. 진입 점수 체크 (선택적)
        score = None
        if self.chk_use_entry_scoring.isChecked():
            score, reasons = self.calculate_entry_score(ticker, curr, info, snapshot=snapshot)
            threshold = self.spin_entry_score_threshold.value()
            if not should_enter_by_score(True, score, threshold):
                reason_summary = ", ".join(reasons[:3]) if reasons else "점수 근거 없음"
                self.log(
                    f"[{ticker}] 진입 점수 {score:.0f} < {threshold} 진입 보류 "
                    f"(근거: {reason_summary})"
                )
                return
        
        # 매수 실행
        if score is None:
            self.log(f"[{ticker}] 진입 조건 충족")
        else:
            self.log(f"[{ticker}] 진입 조건 충족 (점수: {score:.0f})")
        self.execute_buy(ticker, curr)

    def _check_sell_condition(self, ticker, curr, info):
        """매도 조건 확인"""
        buy_p = info['buy_price']
        if buy_p == 0:
            return
        
        profit_rate = (curr - buy_p) / buy_p * 100
        
        # 최고가 갱신
        if curr > info['high_since_buy']:
            info['high_since_buy'] = curr
            info['max_profit_rate'] = profit_rate
        
        # UI 업데이트
        row = info['row']
        profit_item = info.get('ui_items', {}).get('profit')
        if profit_item is None:
            profit_item = QTableWidgetItem("-")
            self.table.setItem(row, 7, profit_item)
            info.setdefault('ui_items', {})['profit'] = profit_item
        profit_item.setText(f"{profit_rate:.2f}%")
        if profit_rate >= 0:
            profit_item.setForeground(QColor("#e63946"))
        else:
            profit_item.setForeground(QColor("#4361ee"))
        max_profit_item = info.get('ui_items', {}).get('max_profit')
        if max_profit_item is None:
            max_profit_item = QTableWidgetItem("-")
            self.table.setItem(row, 8, max_profit_item)
            info.setdefault('ui_items', {})['max_profit'] = max_profit_item
        max_profit_item.setText(f"{info['max_profit_rate']:.2f}%")
        
        # 1. 손절
        loss_limit = -self.spin_loss.value()
        if profit_rate <= loss_limit:
            self.log(f"🛑 [{ticker}] 손절 조건 ({profit_rate:.2f}%) → 매도")
            self.execute_sell(ticker, "손절")
            return

        # 1-1. v3.0: 시간 기반 청산
        if self.strategy and hasattr(self, 'spin_max_holding_hours'):
            if self.strategy.check_holding_time_exit(ticker, self.spin_max_holding_hours.value()):
                self.execute_sell(ticker, "시간청산")
                return
        
        # 2. 분할 익절 (v2.7 신규)
        if hasattr(self, 'chk_use_partial_tp') and self.chk_use_partial_tp.isChecked():
            partial_sold = info.get('partial_sold', [])
            for level in Config.PARTIAL_TAKE_PROFIT:
                rate = level['rate']
                sell_ratio = level['sell_ratio']
                
                # 이 레벨에서 이미 매도했는지 확인
                if rate in partial_sold:
                    continue
                
                # 수익률 조건 충족
                if profit_rate >= rate and sell_ratio > 0:
                    partial_qty = info['qty'] * (sell_ratio / 100)
                    if partial_qty * curr >= 5000:  # 최소 주문금액 확인
                        if self._execute_partial_sell(ticker, partial_qty, f"분할익절 {rate}%", level=rate):
                            self.log(f"💰 [{ticker}] {rate}% 도달 → {sell_ratio}% 분할 익절")
                            return  # 한 번에 하나의 분할 매도만
        
        # 3. 트레일링 스톱
        ts_start = self.spin_ts_start.value()
        ts_stop = self.spin_ts_stop.value()
        
        if info['max_profit_rate'] >= ts_start:
            drop = (info['high_since_buy'] - curr) / info['high_since_buy'] * 100
            if drop >= ts_stop:
                self.log(f"🎯 [{ticker}] 트레일링 스톱 (고점 대비 -{drop:.2f}%) → 이익 실현")
                self.execute_sell(ticker, "TS")

    # ------------------------------------------------------------------
    # 주문 실행
    # ------------------------------------------------------------------

    def execute_buy(self, ticker, curr_price):
        """매수 주문"""
        if not self.upbit:
            return

        self._ensure_order_stability_state()
        if self.order_service.has_pending(ticker):
            pending = self.order_service.get_pending(ticker)
            self.log(f"[{ticker}] 중복 주문 방지: {pending['side']} 주문 대기 중")
            return
        
        if self.strategy:
            ratio = self.strategy.calculate_dynamic_position_size(ticker) / 100
        else:
            ratio = self.spin_betting.value() / 100
        available_krw = self._get_available_krw()
        bet_cash = available_krw * ratio
        
        if bet_cash < 5000:  # 업비트 최소 주문금액
            self.log(f"[{ticker}] 매수금액 부족 (최소 5,000원)")
            return
        session_id = getattr(self, "_active_session_id", 0)
        if not self._reserve_krw_for_buy(ticker, bet_cash, session_id=session_id):
            self.log(f"[{ticker}] 사용 가능 잔고 부족 (가용: {self._get_available_krw():,.0f}원)")
            return
        
        try:
            # 시장가 매수
            ok, result, err_msg = self.order_service.place_buy_market(
                self.upbit,
                ticker,
                bet_cash,
                pending_meta={
                    "session_id": session_id,
                    "source": "auto_buy",
                    "reserved_krw": bet_cash,
                },
            )
            
            if ok and result and 'uuid' in result:
                info = self.universe.get(ticker)
                if info:
                    info['state'] = '주문중'
                    self.set_table_item(info['row'], 4, "⏳ 주문중", "#ffc107")
                
                self.log(f"📤 [{ticker}] 매수 주문: {bet_cash:,.0f}원")
                self.logger.info(f"매수 주문: {ticker} {bet_cash:,.0f}원")
                
                # 체결 확인
                QTimer.singleShot(
                    2000,
                    lambda t=ticker, u=result['uuid'], s=session_id: self.check_buy_execution(
                        t, u, retry_count=0, session_id=s
                    ),
                )
            else:
                self._release_reserved_krw(ticker)
                self.log(f"[ERROR] 매수 주문 실패: {err_msg} / {result}")
                
        except Exception as e:
            self.order_service.clear_pending(ticker)
            self._release_reserved_krw(ticker)
            self.log(f"[ERROR] 매수 주문 실패: {e}")
            self.logger.error(f"매수 주문 실패 ({ticker}): {e}")

    def check_buy_execution(self, ticker, uuid, retry_count=0, session_id=None):
        """매수 체결 확인 (최대 30회 재시도, 60초 타임아웃)"""
        MAX_RETRIES = 30  # 최대 30회 (60초)
        if hasattr(self, "_ensure_order_stability_state"):
            self._ensure_order_stability_state()
        pending = self.order_service.get_pending(ticker)
        if not pending:
            return
        if pending and str(pending.get("uuid")) != str(uuid):
            return
        clear_pending_if_uuid = getattr(self.order_service, "clear_pending_if_uuid", None)
        release_reserved = getattr(self, "_release_reserved_krw", None)

        try:
            if hasattr(self, "_safe_get_order"):
                order = self._safe_get_order(uuid)
            else:
                order = self.upbit.get_order(uuid)
            state = str(order.get("state", "")).lower() if order else "wait"
            if pending and hasattr(self.order_service, "update_pending"):
                self.order_service.update_pending(
                    ticker,
                    last_checked_at=datetime.datetime.now(),
                    retry_count=int(pending.get("retry_count", 0) or 0) + 1,
                )

            if session_id is not None and session_id != getattr(self, "_active_session_id", 0):
                if state in ("done", "cancel"):
                    if callable(clear_pending_if_uuid):
                        cleared = self.order_service.clear_pending_if_uuid(ticker, uuid)
                    else:
                        self.order_service.clear_pending(ticker)
                        cleared = True
                    if cleared and callable(release_reserved):
                        release_reserved(ticker)
                return

            if state == 'done':
                info = self.universe.get(ticker)

                # 체결 정보
                executed_volume, total_price, avg_price = self.order_service.get_buy_fill_metrics(order)

                if executed_volume > 0 and total_price > 0:
                    if info:
                        info['qty'] = executed_volume
                        info['buy_price'] = avg_price
                        info['invest_amt'] = total_price
                        info['high_since_buy'] = avg_price
                        info['max_profit_rate'] = 0.0
                        info['partial_sold'] = []
                        info['state'] = '보유중'

                        if self.strategy:
                            self.strategy.set_holding_start(ticker)
                            self.strategy.clear_recent_prices(ticker)
                            self.strategy.clear_partial_profit(ticker)

                        row = info['row']
                        qty_item = info.get('ui_items', {}).get('qty')
                        if qty_item is None:
                            qty_item = QTableWidgetItem("-")
                            self.table.setItem(row, 5, qty_item)
                            info.setdefault('ui_items', {})['qty'] = qty_item
                        qty_item.setText(f"{executed_volume:.8f}")

                        buy_price_item = info.get('ui_items', {}).get('buy_price')
                        if buy_price_item is None:
                            buy_price_item = QTableWidgetItem("-")
                            self.table.setItem(row, 6, buy_price_item)
                            info.setdefault('ui_items', {})['buy_price'] = buy_price_item
                        buy_price_item.setText(f"{avg_price:,.0f}")

                        invest_item = info.get('ui_items', {}).get('invest')
                        if invest_item is None:
                            invest_item = QTableWidgetItem("-")
                            self.table.setItem(row, 9, invest_item)
                            info.setdefault('ui_items', {})['invest'] = invest_item
                        invest_item.setText(f"{total_price:,.0f}")
                        self.set_table_item(row, 4, "💼 보유중", "#00b4d8")

                    self.log(f"✅ [{ticker}] 매수 체결: {executed_volume:.8f} @ {avg_price:,.0f}원")
                    self.add_trade_record(ticker, 'BUY', avg_price, executed_volume, 0, '매수 체결')
                    self.get_balance()
                else:
                    if info:
                        info['state'] = '감시중'
                        self.set_table_item(info['row'], 4, "👀 감시중", "#00b894")
                    self.log(f"⚠️ [{ticker}] 매수 체결 정보가 유효하지 않습니다(수량/금액 0). 상태를 감시중으로 복원합니다.")
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                if callable(release_reserved):
                    release_reserved(ticker)
            elif state == 'cancel':
                # 주문 취소됨
                info = self.universe.get(ticker)
                if info:
                    info['state'] = '감시중'
                    self.set_table_item(info['row'], 4, "👀 감시중", "#00b894")
                self.log(f"⚠️ [{ticker}] 매수 주문 취소됨")
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                if callable(release_reserved):
                    release_reserved(ticker)
            else:
                # 아직 체결 안됨, 재시도 횟수 확인
                if retry_count < MAX_RETRIES:
                    QTimer.singleShot(
                        2000,
                        lambda t=ticker, u=uuid, rc=retry_count + 1, s=session_id: self.check_buy_execution(
                            t, u, rc, s
                        ),
                    )
                else:
                    self.log(f"[ERROR] [{ticker}] 매수 체결 확인 타임아웃 (60초)")
                    self.logger.error(f"매수 체결 확인 타임아웃: {ticker}, uuid={uuid}")
                    info = self.universe.get(ticker)
                    if info:
                        info['state'] = '체결확인실패'
                        self.set_table_item(info['row'], 4, "❓ 확인필요", "#ffc107")
                    if callable(clear_pending_if_uuid):
                        clear_pending_if_uuid(ticker, uuid)
                    else:
                        self.order_service.clear_pending(ticker)
                    if callable(release_reserved):
                        release_reserved(ticker)
        except Exception as e:
            if callable(clear_pending_if_uuid):
                clear_pending_if_uuid(ticker, uuid)
            else:
                self.order_service.clear_pending(ticker)
            if callable(release_reserved):
                release_reserved(ticker)
            self.logger.error(f"체결 확인 실패 ({ticker}): {e}")

    def execute_sell(self, ticker, reason):
        """매도 주문"""
        if not self.upbit:
            return

        self._ensure_order_stability_state()
        if self.order_service.has_pending(ticker):
            pending = self.order_service.get_pending(ticker)
            self.log(f"[{ticker}] 중복 주문 방지: {pending['side']} 주문 대기 중")
            return
        
        info = self.universe.get(ticker)
        if not info:
            self.log(f"[WARN] {ticker} 보유 정보를 찾을 수 없어 매도를 건너뜁니다.")
            return

        qty = info['qty']
        if qty == 0:
            return
        session_id = getattr(self, "_active_session_id", 0)
        
        try:
            ok, result, err_msg = self.order_service.place_sell_market(
                self.upbit,
                ticker,
                qty,
                side="SELL",
                pending_meta={
                    "session_id": session_id,
                    "source": "auto_sell",
                },
            )
            
            if ok and result and 'uuid' in result:
                info['state'] = '매도주문중'
                self.set_table_item(info['row'], 4, "⏳ 매도주문중", "#ffc107")
                self.log(f"📤 [{ticker}] 매도 주문: {qty:.8f} ({reason})")
                self.logger.info(f"매도 주문: {ticker} {qty:.8f} ({reason})")
                
                QTimer.singleShot(
                    2000,
                    lambda t=ticker, u=result['uuid'], r=reason, s=session_id: self.check_sell_execution(
                        t, u, r, retry_count=0, session_id=s
                    ),
                )
            else:
                self.log(f"[ERROR] 매도 주문 실패: {err_msg} / {result}")
                
        except Exception as e:
            self.order_service.clear_pending(ticker)
            self.log(f"[ERROR] 매도 주문 실패: {e}")
            self.logger.error(f"매도 주문 실패 ({ticker}): {e}")

    def _execute_partial_sell(self, ticker, qty, reason, level=None):
        """부분 매도 주문 (v2.7 신규 - 분할 익절용)"""
        if not self.upbit:
            return False
        
        info = self.universe.get(ticker)
        if not info or qty <= 0:
            return False
        
        if self.order_service.has_pending(ticker):
            pending = self.order_service.get_pending(ticker)
            self.log(f"[{ticker}] 중복 주문 방지: {pending['side']} 주문 대기 중")
            return False

        session_id = getattr(self, "_active_session_id", 0)
        try:
            ok, result, err_msg = self.order_service.place_sell_market(
                self.upbit,
                ticker,
                qty,
                side="PARTIAL_SELL",
                pending_meta={
                    "session_id": session_id,
                    "source": "partial_sell",
                },
            )
            
            if ok and result and 'uuid' in result:
                self.log(f"📤 [{ticker}] 분할 매도: {qty:.8f} ({reason})")
                self.logger.info(f"분할 매도: {ticker} {qty:.8f} ({reason})")
                
                # 체결 확인 (분할 매도용)
                QTimer.singleShot(
                    2000,
                    lambda t=ticker, u=result['uuid'], q=qty, r=reason, lv=level, s=session_id: self._check_partial_sell_execution(
                        t, u, q, r, lv, retry_count=0, session_id=s
                    ),
                )
                return True
            else:
                self.log(f"[ERROR] 분할 매도 실패: {err_msg} / {result}")
                return False
                
        except Exception as e:
            self.order_service.clear_pending(ticker)
            self.log(f"[ERROR] 분할 매도 실패: {e}")
            self.logger.error(f"분할 매도 실패 ({ticker}): {e}")
            return False

    def _check_partial_sell_execution(self, ticker, uuid, qty, reason, level=None, retry_count=0, session_id=None):
        """분할 매도 체결 확인"""
        MAX_RETRIES = 30
        pending = self.order_service.get_pending(ticker)
        if not pending:
            return
        if pending and str(pending.get("uuid")) != str(uuid):
            return
        clear_pending_if_uuid = getattr(self.order_service, "clear_pending_if_uuid", None)

        try:
            if hasattr(self, "_safe_get_order"):
                order = self._safe_get_order(uuid)
            else:
                order = self.upbit.get_order(uuid)
            state = str(order.get("state", "")).lower() if order else "wait"
            if pending and hasattr(self.order_service, "update_pending"):
                self.order_service.update_pending(
                    ticker,
                    last_checked_at=datetime.datetime.now(),
                    retry_count=int(pending.get("retry_count", 0) or 0) + 1,
                )

            if session_id is not None and session_id != getattr(self, "_active_session_id", 0):
                if state in ("done", "cancel"):
                    if callable(clear_pending_if_uuid):
                        clear_pending_if_uuid(ticker, uuid)
                    else:
                        self.order_service.clear_pending(ticker)
                return

            if state == 'done':
                info = self.universe.get(ticker)
                if not info:
                    if callable(clear_pending_if_uuid):
                        clear_pending_if_uuid(ticker, uuid)
                    else:
                        self.order_service.clear_pending(ticker)
                    return

                executed_volume, _, trades_price = self.order_service.get_sell_fill_metrics(order)

                if executed_volume <= 0 or trades_price <= 0:
                    self.log(f"⚠️ [{ticker}] 분할 매도 체결 정보가 유효하지 않습니다.")
                    if callable(clear_pending_if_uuid):
                        clear_pending_if_uuid(ticker, uuid)
                    else:
                        self.order_service.clear_pending(ticker)
                    return
                
                # 보유 수량 감소
                info['qty'] -= executed_volume
                if info['qty'] < 0:
                    info['qty'] = 0
                
                # 손익 계산 (부분)
                info['invest_amt'], profit = self.order_service.apply_partial_sell_accounting(
                    info['invest_amt'], info['qty'], executed_volume, trades_price
                )
                
                self.total_realized_profit += profit
                self.trade_count += 1
                if profit > 0:
                    self.win_count += 1
                
                # UI 업데이트
                self.lbl_total_profit.setText(f"📈 당일 실현손익: {self.total_realized_profit:,.0f}원")
                qty_item = info.get('ui_items', {}).get('qty')
                if qty_item is None:
                    qty_item = QTableWidgetItem("-")
                    self.table.setItem(info['row'], 5, qty_item)
                    info.setdefault('ui_items', {})['qty'] = qty_item
                qty_item.setText(f"{info['qty']:.8f}")
                
                self.log(f"✅ [{ticker}] 분할 매도 체결 (손익: {profit:+,.0f}원)")
                self.add_trade_record(ticker, 'PARTIAL_SELL', trades_price, executed_volume, profit, reason)
                if level is not None and level not in info.setdefault('partial_sold', []):
                    info['partial_sold'].append(level)
                self._update_statistics()
                
                self.get_balance()
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
            elif state == 'cancel':
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
                self.log(f"⚠️ [{ticker}] 분할 매도 주문 취소됨")
            else:
                if retry_count < MAX_RETRIES:
                    QTimer.singleShot(
                        2000,
                        lambda t=ticker, u=uuid, q=qty, r=reason, lv=level, rc=retry_count + 1, s=session_id: self._check_partial_sell_execution(
                            t, u, q, r, lv, rc, s
                        ),
                    )
                else:
                    self.log(f"[ERROR] [{ticker}] 분할 매도 체결 확인 타임아웃")
                    if callable(clear_pending_if_uuid):
                        clear_pending_if_uuid(ticker, uuid)
                    else:
                        self.order_service.clear_pending(ticker)
        except Exception as e:
            if callable(clear_pending_if_uuid):
                clear_pending_if_uuid(ticker, uuid)
            else:
                self.order_service.clear_pending(ticker)
            self.logger.error(f"분할 매도 체결 확인 실패 ({ticker}): {e}")

    def check_sell_execution(self, ticker, uuid, reason, retry_count=0, session_id=None):
        """매도 체결 확인 (최대 30회 재시도, 60초 타임아웃)"""
        MAX_RETRIES = 30  # 최대 30회 (60초)
        pending = self.order_service.get_pending(ticker)
        if not pending:
            return
        if pending and str(pending.get("uuid")) != str(uuid):
            return
        clear_pending_if_uuid = getattr(self.order_service, "clear_pending_if_uuid", None)

        try:
            if hasattr(self, "_safe_get_order"):
                order = self._safe_get_order(uuid)
            else:
                order = self.upbit.get_order(uuid)
            state = str(order.get("state", "")).lower() if order else "wait"
            if pending and hasattr(self.order_service, "update_pending"):
                self.order_service.update_pending(
                    ticker,
                    last_checked_at=datetime.datetime.now(),
                    retry_count=int(pending.get("retry_count", 0) or 0) + 1,
                )

            if session_id is not None and session_id != getattr(self, "_active_session_id", 0):
                if state in ("done", "cancel"):
                    if callable(clear_pending_if_uuid):
                        clear_pending_if_uuid(ticker, uuid)
                    else:
                        self.order_service.clear_pending(ticker)
                return

            if state == 'done':
                info = self.universe.get(ticker)
                if not info:
                    if callable(clear_pending_if_uuid):
                        clear_pending_if_uuid(ticker, uuid)
                    else:
                        self.order_service.clear_pending(ticker)
                    return

                executed_volume, sell_amount, trades_price = self.order_service.get_sell_fill_metrics(order)

                if executed_volume <= 0 or sell_amount <= 0:
                    info['state'] = '보유중'
                    self.set_table_item(info['row'], 4, "💼 보유중", "#00b4d8")
                    self.log(f"⚠️ [{ticker}] 매도 체결 정보가 유효하지 않습니다.")
                    if callable(clear_pending_if_uuid):
                        clear_pending_if_uuid(ticker, uuid)
                    else:
                        self.order_service.clear_pending(ticker)
                    return
                
                # 손익 계산
                buy_amount = info['invest_amt']
                profit = sell_amount - buy_amount
                
                self.total_realized_profit += profit
                self.trade_count += 1
                if profit > 0:
                    self.win_count += 1
                
                # UI 업데이트
                profit_text = f"📈 당일 실현손익: {self.total_realized_profit:,.0f}원"
                self.lbl_total_profit.setText(profit_text)
                
                info['qty'] = 0
                info['state'] = '매도완료'
                info['partial_sold'] = []
                self.set_table_item(info['row'], 4, "✅ 청산완료", "#6c757d")

                if self.strategy:
                    self.strategy.update_consecutive_results(profit > 0)
                    self.strategy.clear_holding_start(ticker)
                    self.strategy.clear_partial_profit(ticker)
                    if hasattr(self, 'chk_use_cooldown') and self.chk_use_cooldown.isChecked():
                        cooldown_minutes = self.spin_cooldown.value() if hasattr(self, 'spin_cooldown') else None
                        self.strategy.set_cooldown(ticker, cooldown_minutes)
                
                self.log(f"✅ [{ticker}] 매도 체결 (손익: {profit:+,.0f}원)")
                self.add_trade_record(ticker, 'SELL', trades_price, executed_volume, profit, reason)
                
                self._update_statistics()
                self.get_balance()
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
            elif state == 'cancel':
                self.log(f"⚠️ [{ticker}] 매도 주문 취소됨")
                info = self.universe.get(ticker)
                if info and info['qty'] > 0:
                    info['state'] = '보유중'
                    self.set_table_item(info['row'], 4, "💼 보유중", "#00b4d8")
                if callable(clear_pending_if_uuid):
                    clear_pending_if_uuid(ticker, uuid)
                else:
                    self.order_service.clear_pending(ticker)
            else:
                if retry_count < MAX_RETRIES:
                    QTimer.singleShot(
                        2000,
                        lambda t=ticker, u=uuid, r=reason, rc=retry_count + 1, s=session_id: self.check_sell_execution(
                            t, u, r, rc, s
                        ),
                    )
                else:
                    self.log(f"[ERROR] [{ticker}] 매도 체결 확인 타임아웃 (60초)")
                    self.logger.error(f"매도 체결 확인 타임아웃: {ticker}, uuid={uuid}")
                    info = self.universe.get(ticker)
                    if info:
                        info['state'] = '체결확인실패'
                        self.set_table_item(info['row'], 4, "❓ 확인필요", "#ffc107")
                    if callable(clear_pending_if_uuid):
                        clear_pending_if_uuid(ticker, uuid)
                    else:
                        self.order_service.clear_pending(ticker)
        except Exception as e:
            if callable(clear_pending_if_uuid):
                clear_pending_if_uuid(ticker, uuid)
            else:
                self.order_service.clear_pending(ticker)
            self.logger.error(f"매도 체결 확인 실패 ({ticker}): {e}")

    # ------------------------------------------------------------------
    # 일괄 매도/매수 기능 (v2.6 신규)
    # ------------------------------------------------------------------

    def check_risk_limits(self):
        """리스크 한도 체크"""
        if not self.chk_use_risk.isChecked():
            return True
        
        # 일일 손실 한도
        if self.initial_balance > 0:
            loss_rate = (self.total_realized_profit / self.initial_balance) * 100
            max_loss = -self.spin_max_loss.value()
            
            if loss_rate <= max_loss:
                if not self.daily_loss_triggered:
                    self.daily_loss_triggered = True
                    self.log(f"🛑 일일 손실 한도 도달! ({loss_rate:.2f}%)")
                return False
        
        # 최대 보유 종목
        holdings = sum(1 for info in self.universe.values() if info['qty'] > 0)
        if holdings >= self.spin_max_holdings.value():
            return False
        
        return True

    def apply_preset(self, preset_type):
        """프리셋 적용"""
        if preset_type in Config.DEFAULT_PRESETS:
            preset = Config.DEFAULT_PRESETS[preset_type]
            self.apply_preset_values(preset)

    def set_table_item(self, row, col, text, bg_color):
        """테이블 아이템 설정"""
        item = self.table.item(row, col)
        if item is None:
            item = QTableWidgetItem(text)
            self.table.setItem(row, col, item)
        else:
            item.setText(text)
        item.setBackground(QColor(bg_color))
        item.setForeground(QColor("#1a1a2e"))

    def _update_statistics(self):
        """통계 업데이트"""
        self.stat_trades.setText(f"📊 총 거래 횟수\n{self.trade_count} 회")
        
        winrate = (self.win_count / self.trade_count * 100) if self.trade_count > 0 else 0
        self.stat_winrate.setText(f"🎯 승률\n{winrate:.1f} %")
        
        self.stat_profit.setText(f"💰 총 실현손익\n{self.total_realized_profit:,.0f} 원")
        
        holdings = sum(1 for info in self.universe.values() if info['qty'] > 0)
        self.stat_holdings.setText(f"📦 보유 종목\n{holdings} 개")

    def reset_statistics(self):
        """통계 초기화"""
        reply = QMessageBox.question(self, "확인", "거래 통계를 초기화하시겠습니까?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.total_realized_profit = 0
            self.trade_count = 0
            self.win_count = 0
            self._update_statistics()
            self.lbl_total_profit.setText("📈 당일 실현손익: 0 원")
            self.log("🔄 통계 초기화됨")

    def log(self, msg):
        """로그 출력 (v2.5 메모리 제한 적용)"""
        t = datetime.datetime.now().strftime("[%H:%M:%S]")
        self.log_text.append(f"{t} {msg}")

        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())
    
    # ------------------------------------------------------------------
    # v2.7: 도구 메뉴 함수
    # ------------------------------------------------------------------


