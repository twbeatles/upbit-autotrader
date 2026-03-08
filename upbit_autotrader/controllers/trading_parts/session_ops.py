from __future__ import annotations

# Runtime bindings injected by trading_controller facade
Config = None
QMessageBox = None
QTableWidgetItem = None
pyupbit = None
time = None


def bind_runtime(**kwargs):
    globals().update(kwargs)



def start_trading(self):
    """매매 시작"""
    allow_paper_no_login = self._is_paper_mode() and self._allow_paper_without_login()
    if (not self.upbit or not self.is_connected) and not allow_paper_no_login:
        QMessageBox.warning(self, "경고", "먼저 업비트 API에 연결해주세요.")
        return

    coins_text = self.input_coins.text().replace(" ", "")
    coins = [c for c in coins_text.split(',') if c]
    invalid_coins = [c for c in coins if not c.startswith("KRW-")]
    if invalid_coins:
        QMessageBox.warning(
            self,
            "경고",
            f"잘못된 코인 코드: {', '.join(invalid_coins)}\n코인 코드는 'KRW-' 형식이어야 합니다.",
        )
        return

    account_holdings = []
    if self._enable_account_wide_sync():
        account_holdings = self._fetch_account_holdings()
    holding_tickers = [
        str(h.get("ticker") or "").strip()
        for h in account_holdings
        if str(h.get("ticker") or "").strip().startswith("KRW-")
    ]
    target_universe = list(dict.fromkeys(coins + holding_tickers))
    if not target_universe:
        QMessageBox.warning(self, "경고", "감시할 코인을 입력하거나 계좌 보유 종목이 있어야 합니다.")
        return

    self.universe = {}
    self.table.setRowCount(0)
    self.is_running = False
    self.daily_loss_triggered = False
    self._ensure_order_stability_state()
    self._price_feed_recovery_attempted = False
    self._last_price_update_ts = time.time()
    self._risk_snapshot_cache = {"ts": 0.0, "value": None}
    self._seed_paper_balance_once()
    if self._is_paper_mode():
        self.get_balance()
        if float(getattr(self, "balance", 0.0) or 0.0) <= 0:
            QMessageBox.warning(self, "경고", "페이퍼 잔고가 0원입니다. 초기 시드를 확인해주세요.")
            self.is_running = False
            return
        if float(getattr(self, "initial_balance", 0.0) or 0.0) <= 0:
            self.initial_balance = float(self.balance)
    self.is_running = True
    self._next_trading_session()
    self._reconcile_pending_orders(force=False)
    self._ensure_indicator_cache_state()
    self._indicator_cache.clear()
    
    self.btn_start.setEnabled(False)
    self.btn_stop.setEnabled(True)
    self.status_trading.setText("● 분석 중")
    self.status_trading.setStyleSheet("color: #00b4d8;")
    
    candle_interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
    holdings_map = self._build_holdings_map(account_holdings)
    self.table.setUpdatesEnabled(False)
    try:
        for coin in target_universe:
            try:
                # 목표가 및 MA 계산
                if self.strategy:
                    target_price = self.strategy.calculate_target_price(coin, candle_interval)
                else:
                    target_price = self.calculate_target_price(coin, candle_interval)
                ma5 = self.calculate_ma(coin, candle_interval, 5)
                holding = holdings_map.get(coin, {})
                holding_qty = float(holding.get("qty", 0.0) or 0.0)
                current_price = float(holding.get("current_price", 0.0) or 0.0)
                if current_price <= 0:
                    current_price = pyupbit.get_current_price(coin) if pyupbit is not None else 0.0

                if target_price is None or ma5 is None:
                    if holding_qty > 0:
                        target_price = float(target_price or 0.0)
                        ma5 = float(ma5 or 0.0)
                    else:
                        self.log(f"[WARN] {coin} 데이터 조회 실패")
                        continue

                buy_price = float(holding.get("buy_price", 0.0) or 0.0)
                invest_amt = float(holding_qty * buy_price) if buy_price > 0 else float(holding.get("value", 0.0) or 0.0)
                state = "보유중" if holding_qty > 0 else "감시중"

                if target_price is None or ma5 is None:
                    self.log(f"[WARN] {coin} 데이터 조회 실패")
                    continue

                self.universe[coin] = {
                    'name': coin,
                    'state': state,
                    'row': len(self.universe),
                    'target': target_price,
                    'ma5': ma5,
                    'current': current_price or 0.0,
                    'qty': holding_qty,
                    'buy_price': buy_price,
                    'invest_amt': invest_amt,
                    'high_since_buy': max(float(current_price or 0.0), buy_price) if holding_qty > 0 else 0.0,
                    'max_profit_rate': 0.0
                }

                row = self.universe[coin]['row']
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(coin))
                self.table.setItem(row, 1, QTableWidgetItem(f"{current_price:,.0f}" if current_price else "-"))
                self.table.setItem(row, 2, QTableWidgetItem(f"{target_price:,.0f}"))
                self.table.setItem(row, 3, QTableWidgetItem(f"{ma5:,.0f}"))
                self.table.setItem(row, 5, QTableWidgetItem(f"{holding_qty:.8f}" if holding_qty > 0 else "0.00000000"))
                self.table.setItem(row, 6, QTableWidgetItem(f"{buy_price:,.0f}" if buy_price > 0 else "-"))
                self.table.setItem(row, 7, QTableWidgetItem("-"))
                self.table.setItem(row, 8, QTableWidgetItem("-"))
                self.table.setItem(row, 9, QTableWidgetItem(f"{invest_amt:,.0f}" if invest_amt > 0 else "-"))
                if holding_qty > 0:
                    self.set_table_item(row, 4, "💼 보유중", "#00b4d8")
                else:
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

                if holding_qty > 0 and self.strategy:
                    self.strategy.set_holding_start(coin)
                    self.strategy.clear_partial_profit(coin)

                self.log(f"[{coin}] 목표가:{target_price:,.0f}, MA5:{ma5:,.0f}")

            except Exception as e:
                self.log(f"[ERROR] {coin} 초기화 실패: {e}")
                self.logger.error(f"{coin} 초기화 실패: {e}")
    finally:
        self.table.setUpdatesEnabled(True)
    if self.universe and self._enable_account_wide_sync():
        self._sync_account_holdings_to_universe(account_holdings=account_holdings, include_external=True)
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
    
    if hasattr(self, "refresh_trade_action_buttons"):
        self.refresh_trade_action_buttons()
    self.btn_stop.setEnabled(False)
    self.status_trading.setText("● 중지됨")
    self.status_trading.setStyleSheet("color: #e63946;")
    self.status_realtime.setText("실시간: 비활성")
    
    self.log("⏹️ 매매가 중지되었습니다")
    self.logger.info("매매 중지")
