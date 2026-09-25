"""Securities-app style order ticket (MTS/HMS patterns).

Single-symbol ticket docked in the strategy tab: symbol + order type +
price/qty inputs, amount presets, paper/live badge, dry-run validation
via POST /v1/order/test, and a confirm gate (live always confirms).
"""
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from upbit_autotrader.core.config import Config


PRESET_PCTS = (10, 25, 50, 100)


def build_order_ticket(self) -> QWidget:
    group = QGroupBox("⚡ 주문 티켓 (단일 종목)")
    layout = QVBoxLayout(group)
    layout.setSpacing(8)

    top = QGridLayout()
    top.setSpacing(8)

    top.addWidget(QLabel("종목:"), 0, 0)
    self.combo_ticket_symbol = QComboBox()
    self.combo_ticket_symbol.setEditable(True)
    for coin in str(Config.DEFAULT_COINS).split(","):
        coin = coin.strip()
        if coin:
            self.combo_ticket_symbol.addItem(coin)
    self.combo_ticket_symbol.setToolTip(Config.TOOLTIPS.get("order_ticket", ""))
    top.addWidget(self.combo_ticket_symbol, 0, 1)

    top.addWidget(QLabel("주문형식:"), 0, 2)
    self.combo_ticket_type = QComboBox()
    self.combo_ticket_type.addItems(["시장가", "지정가", "최유리"])
    self.combo_ticket_type.setToolTip(Config.TOOLTIPS.get("order_ticket", ""))
    top.addWidget(self.combo_ticket_type, 0, 3)

    self.lbl_ticket_mode = QLabel("LIVE")
    self.lbl_ticket_mode.setStyleSheet("font-weight: bold;")
    top.addWidget(self.lbl_ticket_mode, 0, 4)
    layout.addLayout(top)

    mid = QGridLayout()
    mid.setSpacing(8)
    mid.addWidget(QLabel("가격(KRW):"), 0, 0)
    self.spin_ticket_price = QDoubleSpinBox()
    self.spin_ticket_price.setRange(0, 1000000000)
    self.spin_ticket_price.setDecimals(0)
    self.spin_ticket_price.setValue(0)
    mid.addWidget(self.spin_ticket_price, 0, 1)

    mid.addWidget(QLabel("수량/금액:"), 0, 2)
    self.spin_ticket_amount = QDoubleSpinBox()
    self.spin_ticket_amount.setRange(0, 1000000000)
    self.spin_ticket_amount.setDecimals(2)
    self.spin_ticket_amount.setValue(0)
    mid.addWidget(self.spin_ticket_amount, 0, 3)
    layout.addLayout(mid)

    preset_row = QHBoxLayout()
    preset_row.setSpacing(6)
    preset_row.addWidget(QLabel("비중:"))
    for pct in PRESET_PCTS:
        btn = QPushButton(f"{pct}%")
        btn.setProperty("ticket_pct", pct)
        btn.clicked.connect(lambda _=False, p=pct: _apply_ticket_preset(self, p))
        preset_row.addWidget(btn)
    preset_row.addStretch(1)
    layout.addLayout(preset_row)

    self.chk_ticket_require_confirm = QCheckBox("주문 전 확인 (LIVE 강제)")
    self.chk_ticket_require_confirm.setChecked(bool(Config.DEFAULT_TICKET_REQUIRE_CONFIRM))
    self.chk_ticket_require_confirm.setToolTip(Config.TOOLTIPS.get("ticket_confirm", ""))
    layout.addWidget(self.chk_ticket_require_confirm)

    btn_row = QHBoxLayout()
    btn_row.setSpacing(8)
    self.btn_ticket_dryrun = QPushButton("🧪 주문 검증")
    self.btn_ticket_dryrun.setToolTip("POST /v1/order/test 호출로 실제 체결 없이 검증합니다.")
    self.btn_ticket_dryrun.clicked.connect(lambda: ticket_dry_run(self))
    self.btn_ticket_buy = QPushButton("📈 매수")
    self.btn_ticket_buy.setStyleSheet(
        "QPushButton { background-color: #c0392b; color: white; font-weight: bold; }"
    )
    self.btn_ticket_buy.clicked.connect(lambda: submit_ticket_order(self, "BUY"))
    self.btn_ticket_sell = QPushButton("📉 매도")
    self.btn_ticket_sell.setStyleSheet(
        "QPushButton { background-color: #2471a3; color: white; font-weight: bold; }"
    )
    self.btn_ticket_sell.clicked.connect(lambda: submit_ticket_order(self, "SELL"))
    btn_row.addWidget(self.btn_ticket_dryrun)
    btn_row.addStretch(1)
    btn_row.addWidget(self.btn_ticket_buy)
    btn_row.addWidget(self.btn_ticket_sell)
    layout.addLayout(btn_row)

    self.lbl_ticket_status = QLabel("대기 중")
    layout.addWidget(self.lbl_ticket_status)
    refresh_ticket_mode_badge(self)
    return group


def refresh_ticket_mode_badge(self) -> None:
    is_paper = bool(callable(getattr(self, "_is_paper_mode", None)) and self._is_paper_mode())
    label = getattr(self, "lbl_ticket_mode", None)
    if label is not None:
        label.setText("PAPER" if is_paper else "LIVE")
        label.setStyleSheet(
            "font-weight: bold; color: %s;" % ("#27ae60" if is_paper else "#c0392b")
        )


def _ticket_values(self):
    symbol = ""
    combo = getattr(self, "combo_ticket_symbol", None)
    if combo is not None and hasattr(combo, "currentText"):
        symbol = str(combo.currentText()).strip()
    kind = "시장가"
    type_combo = getattr(self, "combo_ticket_type", None)
    if type_combo is not None and hasattr(type_combo, "currentText"):
        kind = str(type_combo.currentText())
    price_spin = getattr(self, "spin_ticket_price", None)
    amount_spin = getattr(self, "spin_ticket_amount", None)
    price = float(price_spin.value()) if price_spin is not None else 0.0
    amount = float(amount_spin.value()) if amount_spin is not None else 0.0
    return symbol, kind, price, amount


def _apply_ticket_preset(self, pct: int) -> None:
    try:
        balance = float(getattr(self, "balance", 0.0) or 0.0)
        spin = getattr(self, "spin_ticket_amount", None)
        if spin is None:
            return
        _, kind, price, _ = _ticket_values(self)
        base = balance * float(pct) / 100.0
        if kind == "시장가":
            spin.setValue(max(0.0, base))
        else:
            qty = (base / price) if price > 0 else 0.0
            spin.setValue(max(0.0, qty))
    except Exception:
        return


def _needs_confirm(self) -> bool:
    is_paper = bool(callable(getattr(self, "_is_paper_mode", None)) and self._is_paper_mode())
    if not is_paper:
        return True
    chk = getattr(self, "chk_ticket_require_confirm", None)
    if chk is not None and hasattr(chk, "isChecked"):
        return bool(chk.isChecked())
    return bool(Config.DEFAULT_TICKET_REQUIRE_CONFIRM)


def ticket_dry_run(self) -> bool:
    symbol, kind, price, amount = _ticket_values(self)
    status = getattr(self, "lbl_ticket_status", None)
    if not symbol:
        if status is not None:
            status.setText("종목을 입력하세요.")
        return False
    upbit = getattr(self, "upbit", None)
    test_fn = getattr(upbit, "test_order", None)
    if not callable(test_fn):
        if status is not None:
            status.setText("연결된 클라이언트가 order/test를 지원하지 않습니다.")
        return False
    side = "bid"
    ord_type, volume, order_price = _to_test_payload(kind, price, amount)
    try:
        res = test_fn(
            market=symbol, side=side, volume=volume, price=order_price, ord_type=ord_type
        )
        ok = isinstance(res, dict) and bool(res.get("uuid") or res.get("market"))
        if status is not None:
            status.setText(f"검증 {'성공' if ok else '응답 확인'}: {res}")
        return ok
    except Exception as exc:
        if status is not None:
            status.setText(f"검증 실패: {exc}")
        return False


def _to_test_payload(kind: str, price: float, amount: float):
    if kind == "지정가":
        return "limit", (amount if amount > 0 else None), (price if price > 0 else None)
    if kind == "최유리":
        return "best", (amount if amount > 0 else None), (price if price > 0 else None)
    return "price", None, (amount if amount > 0 else None)


def submit_ticket_order(self, side: str) -> bool:
    symbol, kind, price, amount = _ticket_values(self)
    status = getattr(self, "lbl_ticket_status", None)
    if not symbol:
        if status is not None:
            status.setText("종목을 입력하세요.")
        return False
    if _needs_confirm(self):
        box = QMessageBox(self) if hasattr(self, "mapToGlobal") else QMessageBox()
        box.setWindowTitle("주문 확인")
        box.setText(f"{symbol} {side} 주문을 실행할까요? ({kind} {amount})")
        box.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        if box.exec() != QMessageBox.StandardButton.Ok:
            if status is not None:
                status.setText("사용자 취소")
            return False
    try:
        if side == "BUY":
            if kind == "시장가":
                ok, res, msg = self._place_buy_order(symbol, amount, source="order_ticket")
            else:
                ok, res, msg = self._place_buy_order(symbol, amount, source="order_ticket")
        else:
            ok, res, msg = self._place_sell_order(symbol, amount, source="order_ticket")
    except AttributeError:
        if status is not None:
            status.setText("주문 컨트롤러가 연결되지 않았습니다.")
        return False
    except Exception as exc:
        if status is not None:
            status.setText(f"주문 실패: {exc}")
        return False
    if status is not None:
        status.setText("주문 접수" if ok else f"주문 실패: {msg or res}")
    refresh_ticket_mode_badge(self)
    return bool(ok)
