from __future__ import annotations

import random
import time
from typing import Any, cast

from PyQt6.QtWidgets import QMessageBox

import uuid
from upbit_autotrader.core.config import Config
from upbit_autotrader.services.pyupbit_compat import pyupbit_fallback
from upbit_autotrader.services.rate_limit import is_rate_limit_error
from upbit_autotrader.services.upbit_client import UpbitRestClient

try:
    import pyupbit
except ImportError:
    pyupbit = pyupbit_fallback



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
        self.lbl_connection.setStyleSheet("color: #00b894; font-weight: bold;")
        if hasattr(self, "refresh_trade_action_buttons"):
            self.refresh_trade_action_buttons()
        self.log(f"✅ 업비트 API 연결 성공 (잔고: {float(balance):,.0f}원)")
        self.logger.info(f"API 연결 성공, 잔고: {float(balance):,.0f}원")
    except Exception as e:
        self.is_connected = False
        self.lbl_connection.setText("● 연결 실패")
        self.lbl_connection.setStyleSheet("color: #e63946; font-weight: bold;")
        self.log(f"❌ API 연결 실패: {e}")
        self.logger.error(f"API 연결 실패: {e}")
        if hasattr(self, "refresh_trade_action_buttons"):
            self.refresh_trade_action_buttons()
        QMessageBox.critical(self, "오류", f"API 연결에 실패했습니다.\n{e}")
