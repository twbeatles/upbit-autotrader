import datetime
import json
import logging
import os
from typing import Any, cast

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from upbit_autotrader.core.config import Config
from upbit_autotrader.ui.components.infobar import notify_or_fallback as _notify_or_fallback
from upbit_autotrader.controllers._type_support import ControllerTypeBase

try:
    from upbit_autotrader.analytics.trading_analytics import UpbitTradingAnalytics
    ANALYTICS_AVAILABLE = True
except ImportError:
    UpbitTradingAnalytics = cast(Any, None)
    ANALYTICS_AVAILABLE = False

try:
    from upbit_autotrader.backtesting.backtester import UpbitBacktestEngine, volatility_breakout_strategy, get_strategy_registry
    BACKTESTER_AVAILABLE = True
except ImportError:
    UpbitBacktestEngine = cast(Any, None)
    volatility_breakout_strategy = cast(Any, None)
    get_strategy_registry = cast(Any, None)
    BACKTESTER_AVAILABLE = False



def _merge_transfers(deposits, withdraws):
    """입금/출금 목록을 시간 내림차순으로 병합 (읽기 전용 표시용)."""
    merged = []
    for item in deposits or []:
        if isinstance(item, dict):
            merged.append({"side": "deposit", "raw": item})
    for item in withdraws or []:
        if isinstance(item, dict):
            merged.append({"side": "withdraw", "raw": item})
    merged.sort(key=lambda e: str(e["raw"].get("created_at") or ""), reverse=True)
    return merged


class TraderHistoryController(ControllerTypeBase):
    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def _extract_record_timestamp(record):
        if not isinstance(record, dict):
            return ""
        raw = record.get("timestamp") or record.get("datetime") or ""
        return str(raw)

    @staticmethod
    def _parse_record_datetime(record):
        raw = TraderHistoryController._extract_record_timestamp(record).strip()
        if not raw:
            return None
        try:
            return datetime.datetime.fromisoformat(raw)
        except Exception:
            return None

    def _ensure_history_flush_state(self):
        if not hasattr(self, "_history_dirty"):
            self._history_dirty = False
        if not hasattr(self, "_history_flush_timer"):
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(self._flush_trade_history)
            self._history_flush_timer = timer

    def _schedule_trade_history_save(self):
        self._ensure_history_flush_state()
        self._history_dirty = True
        self._history_flush_timer.start(Config.HISTORY_FLUSH_DEBOUNCE_MS)

    def _flush_trade_history(self):
        self._ensure_history_flush_state()
        if not self._history_dirty:
            return
        self._save_trade_history_now()
        self._history_dirty = False

    def _save_trade_history_now(self):
        with open(Config.TRADE_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.trade_history, f, ensure_ascii=False, indent=2)

    def create_history_tab(self):
        """거래 내역 탭 (v2.5 신규)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 상단 버튼 영역
        btn_layout = QHBoxLayout()
        
        self.lbl_history_count = QLabel("📝 총 0건의 거래 기록")
        btn_layout.addWidget(self.lbl_history_count)
        
        btn_layout.addStretch(1)
        
        btn_clear = QPushButton("🗑️ 오늘 기록 삭제")
        btn_clear.clicked.connect(self.clear_today_history)
        btn_layout.addWidget(btn_clear)
        
        btn_export = QPushButton("💾 내보내기")
        btn_export.clicked.connect(self.export_history)
        btn_layout.addWidget(btn_export)
        
        layout.addLayout(btn_layout)
        
        # 거래 내역 테이블
        self.history_table = QTableWidget()
        history_cols = ["시간", "코인", "구분", "가격", "금액", "손익", "사유"]
        self.history_table.setColumnCount(len(history_cols))
        self.history_table.setHorizontalHeaderLabels(history_cols)
        header = self.history_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        vertical_header = self.history_table.verticalHeader()
        if vertical_header is not None:
            vertical_header.setDefaultSectionSize(30)
        
        layout.addWidget(self.history_table)
        
        # 기존 히스토리 로드
        self._load_history_to_table()
        
        return widget

    def _load_history_to_table(self):
        """기존 거래 기록을 테이블에 로드"""
        for record in self.trade_history:
            self._add_history_row(record)
        self.lbl_history_count.setText(f"📝 총 {len(self.trade_history)}건의 거래 기록")

    def create_transfer_tab(self):
        """입출금 내역 탭 (읽기 전용 조회, 자동 출금 없음)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("통화:"))
        self.input_transfer_currency = QLineEdit()
        self.input_transfer_currency.setPlaceholderText("예: BTC (비우면 전체)")
        filter_layout.addWidget(self.input_transfer_currency)
        filter_layout.addWidget(QLabel("건수:"))
        self.spin_transfer_limit = QSpinBox()
        self.spin_transfer_limit.setRange(1, 100)
        self.spin_transfer_limit.setValue(20)
        filter_layout.addWidget(self.spin_transfer_limit)
        btn_refresh = QPushButton("🔄 조회")
        btn_refresh.setToolTip("입금/출금 목록을 거래소에서 조회합니다. (읽기 전용)")
        btn_refresh.clicked.connect(self.refresh_transfer_history)
        filter_layout.addWidget(btn_refresh)
        filter_layout.addStretch(1)
        layout.addLayout(filter_layout)

        self.lbl_transfer_status = QLabel("조회 버튼을 눌러 입출금 내역을 불러오세요.")
        layout.addWidget(self.lbl_transfer_status)

        self.transfer_table = QTableWidget()
        transfer_cols = ["시간", "종류", "통화", "금액", "상태", "TXID"]
        self.transfer_table.setColumnCount(len(transfer_cols))
        self.transfer_table.setHorizontalHeaderLabels(transfer_cols)
        transfer_header = self.transfer_table.horizontalHeader()
        if transfer_header is not None:
            transfer_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.transfer_table.setAlternatingRowColors(True)
        self.transfer_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.transfer_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.transfer_table)
        return widget

    def refresh_transfer_history(self):
        """입출금 목록 조회 후 테이블 갱신."""
        upbit = getattr(self, "upbit", None)
        deposits_fn = getattr(upbit, "get_deposits", None)
        withdraws_fn = getattr(upbit, "get_withdraws", None)
        if not callable(deposits_fn) or not callable(withdraws_fn):
            self.lbl_transfer_status.setText("API 연결 후 조회할 수 있습니다.")
            return
        currency_widget = getattr(self, "input_transfer_currency", None)
        currency = ""
        if currency_widget is not None and hasattr(currency_widget, "text"):
            currency = str(currency_widget.text()).strip().upper()
        limit_widget = getattr(self, "spin_transfer_limit", None)
        limit = 20
        if limit_widget is not None and hasattr(limit_widget, "value"):
            limit = int(limit_widget.value())
        try:
            raw_deposits: Any = deposits_fn(currency=currency or None, limit=limit)
            raw_withdraws: Any = withdraws_fn(currency=currency or None, limit=limit)
            deposits = list(raw_deposits or [])
            withdraws = list(raw_withdraws or [])
        except Exception as e:
            self.lbl_transfer_status.setText(f"조회 실패: {e}")
            return
        self.transfer_table.setRowCount(0)
        for entry in _merge_transfers(deposits, withdraws):
            raw = entry["raw"]
            row = self.transfer_table.rowCount()
            self.transfer_table.insertRow(row)
            created = str(raw.get("created_at") or "")[:16].replace("T", " ")
            self.transfer_table.setItem(row, 0, QTableWidgetItem(created or "-"))
            kind_item = QTableWidgetItem("📥 입금" if entry["side"] == "deposit" else "📤 출금")
            kind_item.setForeground(QColor("#e63946" if entry["side"] == "deposit" else "#4361ee"))
            self.transfer_table.setItem(row, 1, kind_item)
            self.transfer_table.setItem(row, 2, QTableWidgetItem(str(raw.get("currency") or "-")))
            try:
                amount_text = f"{float(raw.get('amount', 0.0) or 0.0):.8f}".rstrip("0").rstrip(".")
            except (TypeError, ValueError):
                amount_text = str(raw.get("amount") or "-")
            self.transfer_table.setItem(row, 3, QTableWidgetItem(amount_text or "-"))
            self.transfer_table.setItem(row, 4, QTableWidgetItem(str(raw.get("status") or raw.get("state") or "-")))
            self.transfer_table.setItem(row, 5, QTableWidgetItem(str(raw.get("txid") or raw.get("tx_id") or "-")))
        self.lbl_transfer_status.setText(f"입금 {len(deposits)}건 · 출금 {len(withdraws)}건")

    def clear_today_history(self):
        """오늘의 거래 기록 삭제"""
        today = datetime.datetime.now().date().isoformat()
        reply = QMessageBox.question(self, "확인", 
            f"오늘({today})의 거래 기록을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            filtered = []
            for record in self.trade_history:
                ts = self._extract_record_timestamp(record)
                if not ts.startswith(today):
                    filtered.append(record)
            self.trade_history = filtered
            self.save_trade_history()
            self.history_table.setRowCount(0)
            self._load_history_to_table()
            self.log("🗑️ 오늘의 거래 기록이 삭제되었습니다")

    def export_history(self):
        """거래 기록 내보내기"""
        if not self.trade_history:
            _notify_or_fallback(self, "info", "알림", "내보낼 거래 기록이 없습니다.", fallback=lambda: QMessageBox.information(self, "알림", "내보낼 거래 기록이 없습니다."))
            return
        
        filename = f"trade_history_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            import csv
            base_fields = ['timestamp', 'ticker', 'type', 'price', 'quantity', 'amount', 'profit', 'reason']
            extra_fields = []
            for row in self.trade_history:
                if not isinstance(row, dict):
                    continue
                for key in row.keys():
                    if key not in base_fields and key not in extra_fields:
                        extra_fields.append(key)
            fieldnames = base_fields + extra_fields
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.trade_history)
            _notify_or_fallback(self, "success", "완료", f"거래 기록이 {filename}에 저장되었습니다.", fallback=lambda: QMessageBox.information(self, "완료", f"거래 기록이 {filename}에 저장되었습니다."))
            self.log(f"💾 거래 기록 내보내기: {filename}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"내보내기 실패: {e}")

    def generate_analytics_report(self):
        """거래 분석 리포트 생성"""
        try:
            if not ANALYTICS_AVAILABLE:
                QMessageBox.warning(self, "경고", "upbit_analytics 모듈을 찾을 수 없습니다.")
                return
            
            analytics = UpbitTradingAnalytics(Config.TRADE_HISTORY_FILE)
            output_path = "analytics_report.html"
            analytics.generate_report_html(output_path)
            
            self.log(f"📊 거래 분석 리포트 생성: {output_path}")
            os.startfile(output_path)
        except Exception as e:
            self.log(f"[ERROR] 분석 리포트 생성 실패: {e}")
            QMessageBox.critical(self, "오류", f"리포트 생성 실패: {e}")

    def run_backtest(self):
        """백테스트 실행"""
        try:
            if not BACKTESTER_AVAILABLE:
                QMessageBox.warning(self, "경고", "upbit_backtester 모듈을 찾을 수 없습니다.")
                return
            
            # 코인 선택
            coins_text = self.input_coins.text().strip()
            if not coins_text:
                QMessageBox.warning(self, "경고", "백테스트할 코인을 입력해주세요.")
                return
            
            ticker = coins_text.split(',')[0].strip()
            
            self.log(f"🧪 [{ticker}] 백테스트 시작...")

            strategy_func = volatility_breakout_strategy
            strategy_params = {}
            strategy_label = "변동성 돌파"
            if callable(get_strategy_registry):
                registry = get_strategy_registry()
                if isinstance(registry, dict) and registry:
                    keys = list(registry.keys())
                    labels = [
                        f"{k} - {registry[k].get('name', k)}"
                        for k in keys
                        if isinstance(registry.get(k), dict)
                    ]
                    keys = [k for k in keys if isinstance(registry.get(k), dict)]
                    if not keys:
                        return
                    selected_label, ok = QInputDialog.getItem(
                        self,
                        "백테스트 전략 선택",
                        "전략:",
                        labels,
                        0,
                        False,
                    )
                    if not ok:
                        return
                    selected_idx = labels.index(selected_label)
                    selected_key = keys[selected_idx]
                    strategy_meta = registry[selected_key]
                    strategy_func = strategy_meta.get("func", volatility_breakout_strategy)
                    strategy_params = dict(strategy_meta.get("params", {}))
                    strategy_label = strategy_meta.get("name", selected_key)
            
            engine = UpbitBacktestEngine(initial_capital=10_000_000)
            result = engine.run_backtest(
                ticker,
                strategy_func,
                interval="day",
                count=200,
                strategy_params=strategy_params,
            )
            
            output_path = "backtest_report.html"
            engine.generate_report(result, output_path)
            
            self.log(f"🧪 [{strategy_label}] 백테스트 완료: 수익률 {result.total_return:.2f}%, 승률 {result.win_rate:.1f}%")
            os.startfile(output_path)
        except Exception as e:
            self.log(f"[ERROR] 백테스트 실패: {e}")
            QMessageBox.critical(self, "오류", f"백테스트 실패: {e}")

    def export_trade_history(self):
        """거래 내역 CSV 내보내기"""
        try:
            if not self.trade_history:
                _notify_or_fallback(self, "info", "알림", "내보낼 거래 내역이 없습니다.", fallback=lambda: QMessageBox.information(self, "알림", "내보낼 거래 내역이 없습니다."))
                return
            
            filename = f"trade_history_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            import csv
            base_fields = ['timestamp', 'ticker', 'type', 'price', 'quantity', 'amount', 'profit', 'reason']
            extra_fields = []
            for row in self.trade_history:
                if not isinstance(row, dict):
                    continue
                for key in row.keys():
                    if key not in base_fields and key not in extra_fields:
                        extra_fields.append(key)
            fieldnames = base_fields + extra_fields
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.trade_history)
            
            self.log(f"💾 거래 내역 내보내기: {filename}")
            os.startfile(os.path.dirname(os.path.abspath(filename)) or '.')
        except Exception as e:
            self.log(f"[ERROR] 내보내기 실패: {e}")
            QMessageBox.critical(self, "오류", f"내보내기 실패: {e}")

    def load_trade_history(self):
        """거래 히스토리 불러오기 (v2.5 신규)"""
        self._ensure_history_flush_state()
        try:
            if os.path.exists(Config.TRADE_HISTORY_FILE):
                with open(Config.TRADE_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self.trade_history = json.load(f)
        except Exception as e:
            self.trade_history = []
            logging.error(f"거래 히스토리 로드 실패: {e}")

    def save_trade_history(self):
        """거래 히스토리 저장 (v2.5 신규)"""
        self._ensure_history_flush_state()
        try:
            if self._history_flush_timer.isActive():
                self._history_flush_timer.stop()
            self._save_trade_history_now()
            self._history_dirty = False
        except Exception as e:
            self.logger.error(f"거래 히스토리 저장 실패: {e}")

    def add_trade_record(self, ticker, trade_type, price, quantity, profit=0, reason="", **extra_fields):
        """거래 기록 추가 (v2.5 신규)"""
        record = {
            'timestamp': datetime.datetime.now().isoformat(),
            'ticker': ticker,
            'type': trade_type,  # 'BUY' or 'SELL'
            'price': price,
            'quantity': quantity,
            'amount': price * quantity,
            'profit': profit,
            'reason': reason
        }
        if extra_fields:
            for key, value in extra_fields.items():
                if value is None:
                    continue
                record[str(key)] = value
        if "fee_krw" in record and "actual_fee_krw" not in record:
            record["actual_fee_krw"] = record["fee_krw"]
        self.trade_history.append(record)
        
        # 히스토리 테이블 업데이트
        if hasattr(self, 'history_table'):
            self._add_history_row(record)
        
        # 자동 저장
        self._schedule_trade_history_save()

    def _add_history_row(self, record):
        """히스토리 테이블에 행 추가"""
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        
        ts = self._parse_record_datetime(record)
        ts_text = ts.strftime("%m/%d %H:%M") if ts else "-"
        ticker = str(record.get('ticker', '-'))
        trade_type = str(record.get('type', '-'))
        price = self._safe_float(record.get('price', 0.0), 0.0)
        amount = self._safe_float(record.get('amount', 0.0), 0.0)
        profit = self._safe_float(record.get('profit', 0.0), 0.0)
        
        self.history_table.setItem(row, 0, QTableWidgetItem(ts_text))
        self.history_table.setItem(row, 1, QTableWidgetItem(ticker))
        
        type_item = QTableWidgetItem(trade_type)
        if trade_type == 'BUY':
            type_item.setForeground(QColor("#e63946"))
        else:
            type_item.setForeground(QColor("#4361ee"))
        self.history_table.setItem(row, 2, type_item)
        
        self.history_table.setItem(row, 3, QTableWidgetItem(f"{price:,.0f}"))
        self.history_table.setItem(row, 4, QTableWidgetItem(f"{amount:,.0f}"))
        
        profit_item = QTableWidgetItem(f"{profit:+,.0f}" if profit else "-")
        if profit > 0:
            profit_item.setForeground(QColor("#e63946"))
        elif profit < 0:
            profit_item.setForeground(QColor("#4361ee"))
        self.history_table.setItem(row, 5, profit_item)
        
        self.history_table.setItem(row, 6, QTableWidgetItem(record.get('reason', '')))

    # ------------------------------------------------------------------
    # v3.0: 긴급 청산
    # ------------------------------------------------------------------



