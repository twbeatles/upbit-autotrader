from __future__ import annotations

import random
import time
from typing import Any, cast

from PyQt6.QtWidgets import QMessageBox

import uuid
from upbit_autotrader.core.config import Config
from upbit_autotrader.services.pyupbit_compat import pyupbit_fallback
from upbit_autotrader.services.rate_limit import is_rate_limit_error
from upbit_autotrader.ui.components.status_badge import set_status_badge
from upbit_autotrader.services.upbit_client import UpbitRestClient

try:
    import pyupbit
except ImportError:
    pyupbit = pyupbit_fallback



def _set_login_busy(self, busy: bool) -> None:
    btn = getattr(self, "btn_login", None)
    if btn is None:
        return
    try:
        btn.setEnabled(not busy)
        btn.setText("접속 중..." if busy else "시스템 접속")
    except Exception:
        pass


def login(self):
    """업비트 API 연결"""
    access = self.input_access.text().strip()
    secret = self.input_secret.text().strip()
    if not access or not secret:
        QMessageBox.warning(self, "경고", "API Access Key와 Secret Key를 입력해주세요.")
        return

    self.log("🔄 업비트 API 연결 시도 중...")
    self.lbl_connection.setText("● 연결 중...")
    set_status_badge(self.lbl_connection, "warning")
    _set_login_busy(self, True)

    try:
        self._ensure_order_stability_state()
        use_native = getattr(Config, "DEFAULT_USE_NATIVE_UPBIT_CLIENT", True)
        if use_native:
            rate_state = getattr(self, "_rate_limit_state", None)
            self.upbit = UpbitRestClient(access, secret, rate_limit_state=rate_state)
        elif pyupbit is not None and pyupbit is not pyupbit_fallback:
            self.upbit = pyupbit.Upbit(access, secret)
        else:
            self.upbit = UpbitRestClient(access, secret)

        balance = self._api_get_balance("KRW")
        if balance is None:
            raise Exception("잔고 조회 실패")

        self.is_connected = True
        self.balance = float(balance)
        self.initial_balance = float(balance)
        self._paper_seeded = False
        self._seed_paper_balance_once()
        self.lbl_balance.setText(f"💰 주문가능금액: {float(balance):,.0f} 원")
        self.lbl_connection.setText("● 연결됨")
        set_status_badge(self.lbl_connection, "success")
        if hasattr(self, "refresh_trade_action_buttons"):
            self.refresh_trade_action_buttons()
        self.log(f"✅ 업비트 API 연결 성공 (잔고: {float(balance):,.0f}원)")
        self.logger.info(f"API 연결 성공, 잔고: {float(balance):,.0f}원")
        _set_login_busy(self, False)
    except Exception as e:
        self.is_connected = False
        self.lbl_connection.setText("● 연결 실패")
        set_status_badge(self.lbl_connection, "error")
        self.log(f"❌ API 연결 실패: {e}")
        self.logger.error(f"API 연결 실패: {e}")
        if hasattr(self, "refresh_trade_action_buttons"):
            self.refresh_trade_action_buttons()
        QMessageBox.critical(self, "오류", f"API 연결에 실패했습니다.\n{e}")
        _set_login_busy(self, False)
