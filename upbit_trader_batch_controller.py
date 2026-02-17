from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QDialog, QMessageBox, QInputDialog

from upbit_holdings_service import get_account_holdings as get_account_holdings_v2

try:
    from upbit_dialogs import EmergencyCloseDialog
    V3_MODULES_AVAILABLE = True
except ImportError:
    EmergencyCloseDialog = None
    V3_MODULES_AVAILABLE = False


class TraderBatchController:
    def get_account_holdings(self):
        """현재 보유 중인 모든 KRW 마켓 코인 조회"""
        if not self.upbit:
            return []

        try:
            holdings = get_account_holdings_v2(self.upbit)
            self.logger.info(f"보유 코인 조회: {len(holdings)}개")
            return holdings
        except Exception as e:
            self.logger.error(f"보유 코인 조회 실패: {e}")
            return []

    def execute_batch_sell(self):
        """모든 보유 코인 일괄 시장가 매도"""
        if not self.upbit:
            QMessageBox.warning(self, "경고", "먼저 API에 연결해주세요.")
            return
        
        # 보유 코인 조회
        holdings = self.get_account_holdings()
        if not holdings:
            QMessageBox.information(self, "알림", "매도할 코인이 없습니다.")
            return
        
        # 보유 목록 문자열 생성
        holdings_text = "\n".join([f"  • {h['ticker']}: {h['qty']:.8f} (약 {h['value']:,.0f}원)" for h in holdings])
        total_value = sum(h['value'] for h in holdings)
        
        # 1차 확인
        reply = QMessageBox.warning(self, "⚠️ 일괄 매도 확인", 
            f"정말로 모든 보유 코인을 매도하시겠습니까?\n\n"
            f"【보유 코인 목록】\n{holdings_text}\n\n"
            f"📊 총 예상 금액: {total_value:,.0f}원\n\n"
            f"⚠️ 이 작업은 취소할 수 없습니다!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 2차 확인 - 코인 개수 입력
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "🔐 2차 확인", 
            f"매도할 코인 개수 '{len(holdings)}'를 입력하세요:")
        
        if not ok or text.strip() != str(len(holdings)):
            QMessageBox.information(self, "취소", "일괄 매도가 취소되었습니다.")
            return
        
        # 일괄 매도 실행
        self.log("=" * 50)
        self.log(f"📤 일괄 매도 시작 (총 {len(holdings)}개 코인)")
        
        sold_count = 0
        table = getattr(self, "table", None)
        if table is not None:
            table.setUpdatesEnabled(False)
        try:
            for holding in holdings:
                ticker = holding['ticker']
                qty = float(holding.get('qty', 0) or 0)
                try:
                    if qty <= 0:
                        self.log(f"  ⚠️ [{ticker}] 보유 수량 0으로 건너뜀")
                        continue

                    if self.order_service.has_pending(ticker):
                        pending = self.order_service.get_pending(ticker)
                        self.log(f"  ⚠️ [{ticker}] 기존 {pending['side']} 주문 대기 중으로 건너뜀")
                        continue

                    # Universe 종목은 기존 매도 체결 루틴(손익/상태 업데이트) 재사용
                    if ticker in self.universe and self.universe[ticker].get('qty', 0) > 0:
                        self.execute_sell(ticker, "일괄매도")
                        if self.order_service.has_pending(ticker):
                            sold_count += 1
                        continue

                    # Universe 외부 종목은 서비스 경유 + 외부 체결확인 루틴 사용
                    ok, result, err_msg = self.order_service.place_sell_market(
                        self.upbit, ticker, qty, side="SELL"
                    )
                    if ok and result and 'uuid' in result:
                        self.log(f"  ✅ [{ticker}] 매도 주문 접수: {qty:.8f}")
                        sold_count += 1
                        QTimer.singleShot(
                            2000,
                            lambda t=ticker, u=result['uuid']: self._check_external_sell_execution(
                                t, u, reason="일괄매도", context_label="일괄 매도"
                            ),
                        )
                    else:
                        self.log(f"  ❌ [{ticker}] 매도 실패: {err_msg} / {result}")
                except Exception as e:
                    self.log(f"  ❌ [{ticker}] 매도 오류: {e}")
        finally:
            if table is not None:
                table.setUpdatesEnabled(True)
        
        self.log(f"📤 일괄 매도 주문 접수 완료: {sold_count}/{len(holdings)} 성공")
        self.log("=" * 50)
        
        # 잔고 갱신
        QTimer.singleShot(3000, self.get_balance)
        
        # 자동매매 시작 옵션 체크
        if hasattr(self, 'chk_auto_start_after_batch') and self.chk_auto_start_after_batch.isChecked():
            QTimer.singleShot(5000, self.start_trading)
            self.log("🚀 5초 후 자동매매를 시작합니다...")

    def execute_batch_buy(self):
        """입력된 코인들 현재가로 일괄 매수"""
        if not self.upbit:
            QMessageBox.warning(self, "경고", "먼저 API에 연결해주세요.")
            return
        
        # 코인 목록 파싱
        coins_text = self.input_coins.text().replace(" ", "")
        coins = list(dict.fromkeys([c for c in coins_text.split(',') if c and c.startswith("KRW-")]))
        
        if not coins:
            QMessageBox.warning(self, "경고", "매수할 코인을 입력해주세요.\n(예: KRW-BTC,KRW-ETH)")
            return
        
        # 잔고 확인
        self.get_balance()
        if self.balance < 5000 * len(coins):
            QMessageBox.warning(self, "경고", 
                f"잔고가 부족합니다.\n필요 최소 금액: {5000 * len(coins):,}원\n현재 잔고: {self.balance:,.0f}원")
            return
        
        # 투자금 계산 (균등 분배)
        invest_per_coin = self.balance / len(coins)
        
        # 1차 확인
        coins_text_display = "\n".join([f"  • {c}: {invest_per_coin:,.0f}원" for c in coins])
        reply = QMessageBox.warning(self, "⚠️ 일괄 매수 확인",
            f"정말로 아래 코인들을 매수하시겠습니까?\n\n"
            f"【매수 계획】\n{coins_text_display}\n\n"
            f"💰 총 투자금: {self.balance:,.0f}원\n"
            f"📊 종목당 투자금: {invest_per_coin:,.0f}원\n\n"
            f"⚠️ 이 작업은 취소할 수 없습니다!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 2차 확인 - 코인 개수 입력
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "🔐 2차 확인",
            f"매수할 코인 개수 '{len(coins)}'를 입력하세요:")
        
        if not ok or text.strip() != str(len(coins)):
            QMessageBox.information(self, "취소", "일괄 매수가 취소되었습니다.")
            return
        
        # 일괄 매수 실행
        self.log("=" * 50)
        self.log(f"📥 일괄 매수 시작 (총 {len(coins)}개 코인, 종목당 {invest_per_coin:,.0f}원)")
        
        bought_count = 0
        table = getattr(self, "table", None)
        if table is not None:
            table.setUpdatesEnabled(False)
        try:
            for coin in coins:
                try:
                    # 실제 매수 금액 (수수료 고려해서 약간 줄임)
                    buy_amount = invest_per_coin * 0.9995
                    if buy_amount < 5000:
                        self.log(f"  ⚠️ [{coin}] 최소 주문금액 미달")
                        continue

                    if self.order_service.has_pending(coin):
                        pending = self.order_service.get_pending(coin)
                        self.log(f"  ⚠️ [{coin}] 기존 {pending['side']} 주문 대기 중으로 건너뜀")
                        continue

                    ok, result, err_msg = self.order_service.place_buy_market(self.upbit, coin, buy_amount)
                    if ok and result and 'uuid' in result:
                        self.log(f"  ✅ [{coin}] 매수 주문 접수: {buy_amount:,.0f}원")
                        bought_count += 1

                        # Universe 종목은 기존 매수 체결 루틴 재사용
                        if coin in self.universe:
                            info = self.universe[coin]
                            info['state'] = '주문중'
                            self.set_table_item(info['row'], 4, "⏳ 주문중", "#ffc107")
                            QTimer.singleShot(2000, lambda t=coin, u=result['uuid']: self.check_buy_execution(t, u))
                        else:
                            QTimer.singleShot(
                                2000,
                                lambda t=coin, u=result['uuid']: self._check_external_buy_execution(
                                    t, u, reason="일괄매수"
                                ),
                            )
                    else:
                        self.log(f"  ❌ [{coin}] 매수 실패: {err_msg} / {result}")
                except Exception as e:
                    self.log(f"  ❌ [{coin}] 매수 오류: {e}")
        finally:
            if table is not None:
                table.setUpdatesEnabled(True)
        
        self.log(f"📥 일괄 매수 주문 접수 완료: {bought_count}/{len(coins)} 성공")
        self.log("=" * 50)
        
        # 잔고 갱신
        QTimer.singleShot(3000, self.get_balance)
        
        # 자동매매 시작 옵션 체크
        if hasattr(self, 'chk_auto_start_after_batch') and self.chk_auto_start_after_batch.isChecked():
            QTimer.singleShot(5000, self.start_trading)
            self.log("🚀 5초 후 자동매매를 시작합니다...")

    # ------------------------------------------------------------------
    # 유틸리티

    def show_emergency_dialog(self):
        """긴급 청산 다이얼로그 표시"""
        if not V3_MODULES_AVAILABLE:
            QMessageBox.warning(self, "경고", "v3.0 모듈을 사용할 수 없습니다.")
            return

        if not self.upbit:
            QMessageBox.warning(self, "경고", "먼저 API에 연결해주세요.")
            return
        
        holdings = self.get_account_holdings()
        dialog = EmergencyCloseDialog(self, holdings)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.execute_emergency_close()

    def execute_emergency_close(self):
        """긴급 전량 청산 실행"""
        if not self.upbit:
            self.log("⚠️ API 미연결 상태입니다")
            return

        holdings = self.get_account_holdings()
        
        if not holdings:
            self.log("⚠️ 청산할 보유 코인이 없습니다")
            return
        
        self.log("🚨 긴급 전량 청산 시작")

        sold_count = 0
        table = getattr(self, "table", None)
        if table is not None:
            table.setUpdatesEnabled(False)
        try:
            for h in holdings:
                ticker = h['ticker']
                qty = h['qty']
                try:
                    if self.order_service.has_pending(ticker):
                        pending = self.order_service.get_pending(ticker)
                        self.log(f"⚠️ [{ticker}] 기존 {pending['side']} 주문 대기 중으로 긴급청산 건너뜀")
                        continue

                    ok, result, err_msg = self.order_service.place_sell_market(
                        self.upbit, ticker, qty, side="SELL"
                    )
                    if ok and result and 'uuid' in result:
                        sold_count += 1
                        self.log(f"🚨 [{ticker}] 긴급 청산 주문 접수 ({qty:.8f})")

                        # Universe에 있는 종목은 기존 체결 확인 루틴으로 손익/상태 업데이트
                        if ticker in self.universe:
                            info = self.universe[ticker]
                            info['state'] = '매도주문중'
                            self.set_table_item(info['row'], 4, "⏳ 매도주문중", "#ffc107")
                            QTimer.singleShot(2000, lambda t=ticker, u=result['uuid']: self.check_sell_execution(t, u, "긴급청산"))
                        else:
                            # Universe 밖 코인은 주문 확인을 최소 로깅/정리 용도로만 수행
                            QTimer.singleShot(
                                2000,
                                lambda t=ticker, u=result['uuid']: self._check_external_sell_execution(
                                    t, u, reason="긴급청산", context_label="긴급 청산"
                                ),
                            )
                    else:
                        self.log(f"[ERROR] [{ticker}] 긴급 청산 주문 실패: {err_msg} / {result}")
                except Exception as e:
                    self.order_service.clear_pending(ticker)
                    self.log(f"[ERROR] {ticker} 긴급 청산 실패: {e}")
        finally:
            if table is not None:
                table.setUpdatesEnabled(True)

        self.log(f"🚨 긴급 전량 청산 주문 완료: {sold_count}/{len(holdings)}")

    def _check_external_buy_execution(self, ticker, uuid, reason="외부매수", retry_count=0):
        """Universe 외부 코인 매수 체결 확인용"""
        MAX_RETRIES = 30
        try:
            order = self.upbit.get_order(uuid)
            if order and order.get('state') == 'done':
                executed_volume, total_cost, avg_price = self.order_service.get_buy_fill_metrics(order)
                if executed_volume > 0 and total_cost > 0:
                    self.log(f"✅ [{ticker}] {reason} 체결 완료: {executed_volume:.8f} @ {avg_price:,.0f}원")
                    self.add_trade_record(ticker, 'BUY', avg_price, executed_volume, 0, reason)
                    self.get_balance()
                else:
                    self.log(f"⚠️ [{ticker}] {reason} 체결 정보가 유효하지 않습니다.")
                self.order_service.clear_pending(ticker)
            elif order and order.get('state') == 'cancel':
                self.order_service.clear_pending(ticker)
                self.log(f"⚠️ [{ticker}] {reason} 주문 취소")
            else:
                if retry_count < MAX_RETRIES:
                    QTimer.singleShot(
                        2000,
                        lambda: self._check_external_buy_execution(ticker, uuid, reason, retry_count + 1),
                    )
                else:
                    self.order_service.clear_pending(ticker)
                    self.log(f"[ERROR] [{ticker}] {reason} 체결 확인 타임아웃")
        except Exception as e:
            self.order_service.clear_pending(ticker)
            self.log(f"[ERROR] [{ticker}] {reason} 체결 확인 실패: {e}")

    def _check_external_sell_execution(self, ticker, uuid, reason="외부매도", context_label="외부 매도", retry_count=0):
        """Universe 외부 코인 매도 체결 확인용"""
        MAX_RETRIES = 30
        try:
            order = self.upbit.get_order(uuid)
            if order and order.get('state') == 'done':
                executed_volume, _, avg_net_price = self.order_service.get_sell_fill_metrics(order)
                if executed_volume > 0 and avg_net_price > 0:
                    self.log(f"✅ [{ticker}] {context_label} 체결 완료")
                    self.add_trade_record(ticker, 'SELL', avg_net_price, executed_volume, 0, reason)
                    self.get_balance()
                else:
                    self.log(f"⚠️ [{ticker}] {context_label} 체결 정보가 유효하지 않습니다.")
                self.order_service.clear_pending(ticker)
            elif order and order.get('state') == 'cancel':
                self.order_service.clear_pending(ticker)
                self.log(f"⚠️ [{ticker}] {context_label} 주문 취소")
            else:
                if retry_count < MAX_RETRIES:
                    QTimer.singleShot(
                        2000,
                        lambda: self._check_external_sell_execution(
                            ticker, uuid, reason, context_label, retry_count + 1
                        ),
                    )
                else:
                    self.order_service.clear_pending(ticker)
                    self.log(f"[ERROR] [{ticker}] {context_label} 체결 확인 타임아웃")
        except Exception as e:
            self.order_service.clear_pending(ticker)
            self.log(f"[ERROR] [{ticker}] {context_label} 체결 확인 실패: {e}")


