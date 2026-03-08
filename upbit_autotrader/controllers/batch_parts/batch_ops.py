from __future__ import annotations

# Runtime bindings injected by batch_controller facade
QDialog = None
QInputDialog = None
QMessageBox = None
QTimer = None
EmergencyCloseDialog = None
V3_MODULES_AVAILABLE = None


def bind_runtime(**kwargs):
    globals().update(kwargs)



def execute_batch_sell(self):
    """모든 보유 코인 일괄 시장가 매도"""
    if not self.upbit and not (hasattr(self, "_is_paper_mode") and self._is_paper_mode()):
        QMessageBox.warning(self, "경고", "먼저 API에 연결해주세요.")
        return
    if hasattr(self, "_ensure_order_stability_state"):
        self._ensure_order_stability_state()
    session_id = getattr(self, "_active_session_id", 0)
    
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
                if hasattr(self, "_place_sell_order"):
                    ok, result, err_msg = self._place_sell_order(
                        ticker,
                        qty,
                        side="SELL",
                        session_id=session_id,
                        source="batch_sell",
                    )
                else:
                    ok, result, err_msg = self.order_service.place_sell_market(
                        self.upbit,
                        ticker,
                        qty,
                        side="SELL",
                        pending_meta={
                            "session_id": session_id,
                            "source": "batch_sell",
                        },
                    )
                if ok and result and 'uuid' in result:
                    if hasattr(self.order_service, "update_pending"):
                        self.order_service.update_pending(
                            ticker,
                            avg_buy_price=float(holding.get("buy_price", 0.0) or 0.0),
                            requested_qty=float(qty or 0.0),
                            sell_reason="일괄매도",
                            context_label="일괄 매도",
                        )
                    self.log(f"  ✅ [{ticker}] 매도 주문 접수: {qty:.8f}")
                    sold_count += 1
                    QTimer.singleShot(
                        2000,
                        lambda t=ticker, u=result['uuid'], s=session_id: self._check_external_sell_execution(
                            t, u, reason="일괄매도", context_label="일괄 매도", retry_count=0, session_id=s
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
    if not self.upbit and not (hasattr(self, "_is_paper_mode") and self._is_paper_mode()):
        QMessageBox.warning(self, "경고", "먼저 API에 연결해주세요.")
        return
    if hasattr(self, "_ensure_order_stability_state"):
        self._ensure_order_stability_state()
    session_id = getattr(self, "_active_session_id", 0)
    
    # 코인 목록 파싱
    coins_text = self.input_coins.text().replace(" ", "")
    coins = list(dict.fromkeys([c for c in coins_text.split(',') if c and c.startswith("KRW-")]))
    
    if not coins:
        QMessageBox.warning(self, "경고", "매수할 코인을 입력해주세요.\n(예: KRW-BTC,KRW-ETH)")
        return

    if hasattr(self, "check_risk_limits"):
        try:
            if not bool(self.check_risk_limits()):
                QMessageBox.warning(self, "경고", "리스크 한도에 걸려 일괄 매수를 진행할 수 없습니다.")
                self.log("⚠️ 리스크 한도에 걸려 일괄 매수 중단")
                return
        except Exception as e:
            self.log(f"[ERROR] 리스크 검사 실패로 일괄 매수를 중단합니다: {e}")
            return
    
    # 잔고 확인
    self.get_balance()
    available_krw = self._get_available_krw() if hasattr(self, "_get_available_krw") else float(self.balance)
    if available_krw < 5000 * len(coins):
        QMessageBox.warning(self, "경고", 
            f"잔고가 부족합니다.\n필요 최소 금액: {5000 * len(coins):,}원\n현재 가용 잔고: {available_krw:,.0f}원")
        return
    
    # 투자금 계산 (균등 분배)
    invest_per_coin = available_krw / len(coins)
    
    # 1차 확인
    coins_text_display = "\n".join([f"  • {c}: {invest_per_coin:,.0f}원" for c in coins])
    reply = QMessageBox.warning(self, "⚠️ 일괄 매수 확인",
        f"정말로 아래 코인들을 매수하시겠습니까?\n\n"
        f"【매수 계획】\n{coins_text_display}\n\n"
        f"💰 총 투자금(가용): {available_krw:,.0f}원\n"
        f"📊 종목당 투자금: {invest_per_coin:,.0f}원\n\n"
        f"⚠️ 이 작업은 취소할 수 없습니다!",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No)
    
    if reply != QMessageBox.StandardButton.Yes:
        return
    
    # 2차 확인 - 코인 개수 입력
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
        for idx, coin in enumerate(coins):
            try:
                # 남은 종목 수 기준으로 가용 잔고를 재분배해 과주문을 방지
                remaining = max(1, len(coins) - idx)
                available_now = self._get_available_krw() if hasattr(self, "_get_available_krw") else float(self.balance)
                buy_amount = (available_now / remaining) * 0.9995
                if buy_amount < 5000:
                    self.log(f"  ⚠️ [{coin}] 최소 주문금액 미달")
                    continue

                if self.order_service.has_pending(coin):
                    pending = self.order_service.get_pending(coin)
                    self.log(f"  ⚠️ [{coin}] 기존 {pending['side']} 주문 대기 중으로 건너뜀")
                    continue

                if hasattr(self, "_reserve_krw_for_buy"):
                    if not self._reserve_krw_for_buy(coin, buy_amount, session_id=session_id):
                        self.log(f"  ⚠️ [{coin}] 가용 잔고 부족으로 건너뜀")
                        continue

                if hasattr(self, "_place_buy_order"):
                    ok, result, err_msg = self._place_buy_order(
                        coin,
                        buy_amount,
                        session_id=session_id,
                        source="batch_buy",
                    )
                else:
                    ok, result, err_msg = self.order_service.place_buy_market(
                        self.upbit,
                        coin,
                        buy_amount,
                        pending_meta={
                            "session_id": session_id,
                            "source": "batch_buy",
                            "reserved_krw": buy_amount,
                        },
                    )
                if ok and result and 'uuid' in result:
                    self.log(f"  ✅ [{coin}] 매수 주문 접수: {buy_amount:,.0f}원")
                    bought_count += 1

                    # Universe 종목은 기존 매수 체결 루틴 재사용
                    if coin in self.universe:
                        info = self.universe[coin]
                        info['state'] = '주문중'
                        self.set_table_item(info['row'], 4, "⏳ 주문중", "#ffc107")
                        QTimer.singleShot(
                            2000,
                            lambda t=coin, u=result['uuid'], s=session_id: self.check_buy_execution(
                                t, u, retry_count=0, session_id=s
                            ),
                        )
                    else:
                        QTimer.singleShot(
                            2000,
                            lambda t=coin, u=result['uuid'], s=session_id: self._check_external_buy_execution(
                                t, u, reason="일괄매수", retry_count=0, session_id=s
                            ),
                        )
                else:
                    if hasattr(self, "_release_reserved_krw"):
                        self._release_reserved_krw(coin)
                    self.log(f"  ❌ [{coin}] 매수 실패: {err_msg} / {result}")
            except Exception as e:
                if hasattr(self, "_release_reserved_krw"):
                    self._release_reserved_krw(coin)
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


def show_emergency_dialog(self):
    """긴급 청산 다이얼로그 표시"""
    if not V3_MODULES_AVAILABLE:
        QMessageBox.warning(self, "경고", "v3.0 모듈을 사용할 수 없습니다.")
        return

    if not self.upbit:
        if hasattr(self, "_is_paper_mode") and self._is_paper_mode():
            pass
        else:
            QMessageBox.warning(self, "경고", "먼저 API에 연결해주세요.")
            return
    
    holdings = self.get_account_holdings()
    dialog = EmergencyCloseDialog(self, holdings)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        self.execute_emergency_close()


def execute_emergency_close(self):
    """긴급 전량 청산 실행"""
    if not self.upbit and not (hasattr(self, "_is_paper_mode") and self._is_paper_mode()):
        self.log("⚠️ API 미연결 상태입니다")
        return
    if hasattr(self, "_ensure_order_stability_state"):
        self._ensure_order_stability_state()
    session_id = getattr(self, "_active_session_id", 0)

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

                if hasattr(self, "_place_sell_order"):
                    ok, result, err_msg = self._place_sell_order(
                        ticker,
                        qty,
                        side="SELL",
                        session_id=session_id,
                        source="emergency_close",
                    )
                else:
                    ok, result, err_msg = self.order_service.place_sell_market(
                        self.upbit,
                        ticker,
                        qty,
                        side="SELL",
                        pending_meta={
                            "session_id": session_id,
                            "source": "emergency_close",
                        },
                    )
                if ok and result and 'uuid' in result:
                    if hasattr(self.order_service, "update_pending"):
                        self.order_service.update_pending(
                            ticker,
                            avg_buy_price=float(h.get("buy_price", 0.0) or 0.0),
                            requested_qty=float(qty or 0.0),
                            sell_reason="긴급청산",
                            context_label="긴급 청산",
                        )
                    sold_count += 1
                    self.log(f"🚨 [{ticker}] 긴급 청산 주문 접수 ({qty:.8f})")

                    # Universe에 있는 종목은 기존 체결 확인 루틴으로 손익/상태 업데이트
                    if ticker in self.universe:
                        info = self.universe[ticker]
                        info['state'] = '매도주문중'
                        self.set_table_item(info['row'], 4, "⏳ 매도주문중", "#ffc107")
                        QTimer.singleShot(
                            2000,
                            lambda t=ticker, u=result['uuid'], s=session_id: self.check_sell_execution(
                                t, u, "긴급청산", retry_count=0, session_id=s
                            ),
                        )
                    else:
                        # Universe 밖 코인은 주문 확인을 최소 로깅/정리 용도로만 수행
                        QTimer.singleShot(
                            2000,
                            lambda t=ticker, u=result['uuid'], s=session_id: self._check_external_sell_execution(
                                t, u, reason="긴급청산", context_label="긴급 청산", retry_count=0, session_id=s
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
