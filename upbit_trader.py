"""
Upbit Pro Algo-Trader v1.0
업비트 OpenAPI 기반 자동매매 프로그램

변동성 돌파 전략 + 이동평균 필터 + 트레일링 스톱
24시간 코인 마켓 최적화
"""

import sys
import os
import json
import datetime
import time
import logging
import threading
from pathlib import Path

try:
    import pyupbit
except ImportError:
    print("pyupbit 라이브러리가 필요합니다. 'pip install pyupbit' 명령으로 설치해주세요.")
    sys.exit(1)

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import QColor, QFont, QAction


# ============================================================================
# 설정 클래스
# ============================================================================
class Config:
    """프로그램 설정 상수"""
    # 기본 코인
    DEFAULT_COINS = "KRW-BTC,KRW-ETH,KRW-XRP"
    
    # 전략 기본값
    DEFAULT_BETTING_RATIO = 10.0
    DEFAULT_K_VALUE = 0.4
    DEFAULT_TS_START = 5.0
    DEFAULT_TS_STOP = 2.0
    DEFAULT_LOSS_CUT = 3.0
    
    # 캔들 설정
    CANDLE_INTERVALS = {
        "1분": "minute1",
        "5분": "minute5",
        "15분": "minute15",
        "30분": "minute30",
        "1시간": "minute60",
        "4시간": "minute240",
        "일봉": "day"
    }
    DEFAULT_CANDLE = "4시간"
    
    # RSI 설정
    DEFAULT_RSI_PERIOD = 14
    DEFAULT_RSI_UPPER = 70
    DEFAULT_USE_RSI = True
    
    # 거래량 설정
    DEFAULT_VOLUME_MULTIPLIER = 1.5
    DEFAULT_USE_VOLUME = True
    
    # 리스크 관리
    DEFAULT_MAX_DAILY_LOSS = 5.0
    DEFAULT_MAX_HOLDINGS = 5
    DEFAULT_USE_RISK_MGMT = True
    
    # 파일 경로
    SETTINGS_FILE = "upbit_settings.json"
    LOG_DIR = "logs"
    
    # 가격 갱신 주기 (초)
    PRICE_UPDATE_INTERVAL = 1


# ============================================================================
# 다크 테마 스타일시트
# ============================================================================
DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #edf2f4;
    font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
}

QGroupBox {
    border: 1px solid #3d5a80;
    border-radius: 8px;
    margin-top: 12px;
    padding: 15px 10px 10px 10px;
    font-weight: bold;
    font-size: 13px;
    color: #90e0ef;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 8px;
}

QPushButton {
    background-color: #3d5a80;
    color: #edf2f4;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: bold;
    font-size: 13px;
}

QPushButton:hover { background-color: #4a6fa5; }
QPushButton:pressed { background-color: #2c4a6e; }
QPushButton:disabled { background-color: #2d2d44; color: #666680; }

QPushButton#loginBtn { background-color: #00b4d8; }
QPushButton#loginBtn:hover { background-color: #0096c7; }
QPushButton#startBtn { background-color: #e63946; font-size: 15px; }
QPushButton#startBtn:hover { background-color: #d62839; }
QPushButton#stopBtn { background-color: #6c757d; }

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #16213e;
    border: 1px solid #3d5a80;
    border-radius: 5px;
    padding: 8px;
    color: #edf2f4;
    selection-background-color: #00b4d8;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #00b4d8;
}

QTableWidget {
    background-color: #16213e;
    alternate-background-color: #1a2744;
    gridline-color: #2d3a5a;
    border: 1px solid #3d5a80;
    border-radius: 8px;
    color: #edf2f4;
}

QTableWidget::item { padding: 8px; border-bottom: 1px solid #2d3a5a; }
QTableWidget::item:selected { background-color: #3d5a80; }

QHeaderView::section {
    background-color: #0f3460;
    color: #90e0ef;
    padding: 10px;
    border: none;
    border-bottom: 2px solid #00b4d8;
    font-weight: bold;
}

QTextEdit {
    background-color: #0d1b2a;
    border: 1px solid #3d5a80;
    border-radius: 8px;
    color: #90e0ef;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 10px;
}

QLabel { color: #b8c5d6; font-size: 12px; }
QLabel#depositLabel { color: #00b4d8; font-weight: bold; font-size: 14px; }
QLabel#profitLabel { color: #f72585; font-weight: bold; font-size: 14px; }

QStatusBar {
    background-color: #0f3460;
    color: #90e0ef;
    border-top: 1px solid #3d5a80;
    font-size: 11px;
}

QTabWidget::pane { border: 1px solid #3d5a80; border-radius: 8px; background-color: #1a1a2e; }
QTabBar::tab {
    background-color: #16213e;
    color: #b8c5d6;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected { background-color: #3d5a80; color: #edf2f4; }
QTabBar::tab:hover:!selected { background-color: #2d3a5a; }

QScrollBar:vertical {
    background-color: #16213e;
    width: 12px;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background-color: #3d5a80;
    border-radius: 6px;
    min-height: 30px;
}
"""


# ============================================================================
# 가격 갱신 스레드
# ============================================================================
class PriceUpdateThread(QThread):
    """실시간 가격 갱신 스레드"""
    price_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.coin_list = []
        self.is_running = False
    
    def set_coins(self, coins):
        self.coin_list = coins
    
    def run(self):
        self.is_running = True
        while self.is_running and self.coin_list:
            try:
                prices = pyupbit.get_current_price(self.coin_list)
                if prices:
                    self.price_updated.emit(prices if isinstance(prices, dict) else {self.coin_list[0]: prices})
            except Exception as e:
                pass
            time.sleep(Config.PRICE_UPDATE_INTERVAL)
    
    def stop(self):
        self.is_running = False


# ============================================================================
# 메인 트레이더 클래스
# ============================================================================
class UpbitProTrader(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # 내부 변수 초기화
        self.upbit = None
        self.universe = {}
        self.balance = 0
        self.initial_balance = 0
        self.total_realized_profit = 0
        self.trade_count = 0
        self.win_count = 0
        self.is_running = False
        self.is_connected = False
        self.daily_loss_triggered = False
        
        # 가격 갱신 스레드
        self.price_thread = PriceUpdateThread()
        self.price_thread.price_updated.connect(self.on_price_update)
        
        # 로깅 설정
        self.setup_logging()
        
        # UI 초기화
        self.init_ui()
        
        # 타이머 설정
        self.setup_timers()
        
        # 설정 불러오기
        self.load_settings()
        
        self.logger.info("프로그램 초기화 완료")

    def setup_logging(self):
        """로깅 시스템 설정"""
        log_dir = Path(Config.LOG_DIR)
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"upbit_{datetime.datetime.now().strftime('%Y%m%d')}.log"
        
        self.logger = logging.getLogger('UpbitTrader')
        self.logger.setLevel(logging.DEBUG)
        
        if not self.logger.handlers:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("Upbit Pro Algo-Trader v1.0 [24H 코인 자동매매]")
        self.setGeometry(100, 100, 1200, 900)
        self.setStyleSheet(DARK_STYLESHEET)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        main_layout.addWidget(self.create_dashboard())
        main_layout.addWidget(self.create_tab_widget())
        main_layout.addWidget(self.create_splitter())
        self.create_statusbar()

    def create_dashboard(self):
        """대시보드 생성"""
        group_dash = QGroupBox("📊 Trading Dashboard")
        layout_dash = QHBoxLayout()
        layout_dash.setSpacing(15)
        
        # API 키 입력
        layout_dash.addWidget(QLabel("Access:"))
        self.input_access = QLineEdit()
        self.input_access.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_access.setMinimumWidth(150)
        self.input_access.setPlaceholderText("Access Key")
        layout_dash.addWidget(self.input_access)
        
        layout_dash.addWidget(QLabel("Secret:"))
        self.input_secret = QLineEdit()
        self.input_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_secret.setMinimumWidth(150)
        self.input_secret.setPlaceholderText("Secret Key")
        layout_dash.addWidget(self.input_secret)
        
        # 접속 버튼
        self.btn_login = QPushButton("🔌 시스템 접속")
        self.btn_login.setObjectName("loginBtn")
        self.btn_login.setMinimumSize(120, 40)
        self.btn_login.clicked.connect(self.login)
        layout_dash.addWidget(self.btn_login)
        
        layout_dash.addSpacing(20)
        
        # 잔고 표시
        self.lbl_balance = QLabel("💰 주문가능금액: 0 원")
        self.lbl_balance.setObjectName("depositLabel")
        layout_dash.addWidget(self.lbl_balance)
        
        # 실현손익 표시
        self.lbl_total_profit = QLabel("📈 당일 실현손익: 0 원")
        self.lbl_total_profit.setObjectName("profitLabel")
        layout_dash.addWidget(self.lbl_total_profit)
        
        layout_dash.addStretch(1)
        
        # 연결 상태
        self.lbl_connection = QLabel("● 연결 대기")
        self.lbl_connection.setStyleSheet("color: #ffc107; font-weight: bold;")
        layout_dash.addWidget(self.lbl_connection)
        
        group_dash.setLayout(layout_dash)
        return group_dash

    def create_tab_widget(self):
        """탭 위젯 생성"""
        tab_widget = QTabWidget()
        tab_widget.addTab(self.create_strategy_tab(), "⚙️ 전략 설정")
        tab_widget.addTab(self.create_advanced_tab(), "🔬 고급 설정")
        tab_widget.addTab(self.create_statistics_tab(), "📊 거래 통계")
        return tab_widget

    def create_strategy_tab(self):
        """전략 설정 탭"""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 감시 코인
        layout.addWidget(QLabel("📋 감시 코인 (콤마 구분):"), 0, 0)
        self.input_coins = QLineEdit(Config.DEFAULT_COINS)
        self.input_coins.setPlaceholderText("예: KRW-BTC,KRW-ETH,KRW-XRP")
        layout.addWidget(self.input_coins, 0, 1, 1, 5)
        
        # 캔들 간격
        layout.addWidget(QLabel("🕐 캔들 간격:"), 1, 0)
        self.combo_candle = QComboBox()
        self.combo_candle.addItems(Config.CANDLE_INTERVALS.keys())
        self.combo_candle.setCurrentText(Config.DEFAULT_CANDLE)
        layout.addWidget(self.combo_candle, 1, 1)
        
        # 투자 비중
        layout.addWidget(QLabel("💵 종목당 투자비중:"), 1, 2)
        self.spin_betting = QDoubleSpinBox()
        self.spin_betting.setRange(1, 100)
        self.spin_betting.setValue(Config.DEFAULT_BETTING_RATIO)
        self.spin_betting.setSuffix(" %")
        layout.addWidget(self.spin_betting, 1, 3)
        
        # K값
        layout.addWidget(QLabel("📐 변동성 K값:"), 1, 4)
        self.spin_k = QDoubleSpinBox()
        self.spin_k.setRange(0.1, 1.0)
        self.spin_k.setSingleStep(0.1)
        self.spin_k.setValue(Config.DEFAULT_K_VALUE)
        layout.addWidget(self.spin_k, 1, 5)
        
        # 트레일링 스톱 발동
        layout.addWidget(QLabel("🎯 TS 발동 수익률:"), 2, 0)
        self.spin_ts_start = QDoubleSpinBox()
        self.spin_ts_start.setRange(0.5, 30.0)
        self.spin_ts_start.setValue(Config.DEFAULT_TS_START)
        self.spin_ts_start.setSuffix(" %")
        layout.addWidget(self.spin_ts_start, 2, 1)
        
        # 트레일링 스톱 하락폭
        layout.addWidget(QLabel("📉 TS 하락폭:"), 2, 2)
        self.spin_ts_stop = QDoubleSpinBox()
        self.spin_ts_stop.setRange(0.5, 15.0)
        self.spin_ts_stop.setValue(Config.DEFAULT_TS_STOP)
        self.spin_ts_stop.setSuffix(" %")
        layout.addWidget(self.spin_ts_stop, 2, 3)
        
        # 손절률
        layout.addWidget(QLabel("🛑 절대 손절률:"), 2, 4)
        self.spin_loss = QDoubleSpinBox()
        self.spin_loss.setRange(0.5, 20.0)
        self.spin_loss.setValue(Config.DEFAULT_LOSS_CUT)
        self.spin_loss.setSuffix(" %")
        layout.addWidget(self.spin_loss, 2, 5)
        
        # 버튼 영역
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_save = QPushButton("💾 설정 저장")
        self.btn_save.clicked.connect(self.save_settings)
        
        self.btn_start = QPushButton("🚀 전략 분석 및 매매 시작")
        self.btn_start.setObjectName("startBtn")
        self.btn_start.setMinimumSize(250, 50)
        self.btn_start.clicked.connect(self.start_trading)
        self.btn_start.setEnabled(False)
        
        self.btn_stop = QPushButton("⏹️ 매매 중지")
        self.btn_stop.setObjectName("stopBtn")
        self.btn_stop.setMinimumSize(120, 50)
        self.btn_stop.clicked.connect(self.stop_trading)
        self.btn_stop.setEnabled(False)
        
        btn_layout.addWidget(self.btn_save)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        
        layout.addLayout(btn_layout, 3, 0, 1, 6)
        return widget

    def create_advanced_tab(self):
        """고급 설정 탭"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # RSI 필터
        group_rsi = QGroupBox("📈 RSI 필터")
        rsi_layout = QGridLayout()
        
        self.chk_use_rsi = QCheckBox("RSI 필터 사용")
        self.chk_use_rsi.setChecked(Config.DEFAULT_USE_RSI)
        rsi_layout.addWidget(self.chk_use_rsi, 0, 0, 1, 2)
        
        rsi_layout.addWidget(QLabel("RSI 상한선:"), 1, 0)
        self.spin_rsi_upper = QSpinBox()
        self.spin_rsi_upper.setRange(50, 90)
        self.spin_rsi_upper.setValue(Config.DEFAULT_RSI_UPPER)
        rsi_layout.addWidget(self.spin_rsi_upper, 1, 1)
        
        rsi_layout.addWidget(QLabel("RSI 기간:"), 1, 2)
        self.spin_rsi_period = QSpinBox()
        self.spin_rsi_period.setRange(5, 30)
        self.spin_rsi_period.setValue(Config.DEFAULT_RSI_PERIOD)
        rsi_layout.addWidget(self.spin_rsi_period, 1, 3)
        
        group_rsi.setLayout(rsi_layout)
        layout.addWidget(group_rsi)
        
        # 거래량 필터
        group_vol = QGroupBox("📊 거래량 필터")
        vol_layout = QGridLayout()
        
        self.chk_use_volume = QCheckBox("거래량 필터 사용")
        self.chk_use_volume.setChecked(Config.DEFAULT_USE_VOLUME)
        vol_layout.addWidget(self.chk_use_volume, 0, 0, 1, 2)
        
        vol_layout.addWidget(QLabel("거래량 배수:"), 1, 0)
        self.spin_volume_mult = QDoubleSpinBox()
        self.spin_volume_mult.setRange(1.0, 5.0)
        self.spin_volume_mult.setSingleStep(0.1)
        self.spin_volume_mult.setValue(Config.DEFAULT_VOLUME_MULTIPLIER)
        vol_layout.addWidget(self.spin_volume_mult, 1, 1)
        
        group_vol.setLayout(vol_layout)
        layout.addWidget(group_vol)
        
        # 리스크 관리
        group_risk = QGroupBox("🛡️ 리스크 관리")
        risk_layout = QGridLayout()
        
        self.chk_use_risk = QCheckBox("리스크 관리 사용")
        self.chk_use_risk.setChecked(Config.DEFAULT_USE_RISK_MGMT)
        risk_layout.addWidget(self.chk_use_risk, 0, 0, 1, 2)
        
        risk_layout.addWidget(QLabel("일일 최대 손실률:"), 1, 0)
        self.spin_max_loss = QDoubleSpinBox()
        self.spin_max_loss.setRange(1.0, 20.0)
        self.spin_max_loss.setValue(Config.DEFAULT_MAX_DAILY_LOSS)
        self.spin_max_loss.setSuffix(" %")
        risk_layout.addWidget(self.spin_max_loss, 1, 1)
        
        risk_layout.addWidget(QLabel("최대 보유 종목:"), 1, 2)
        self.spin_max_holdings = QSpinBox()
        self.spin_max_holdings.setRange(1, 20)
        self.spin_max_holdings.setValue(Config.DEFAULT_MAX_HOLDINGS)
        risk_layout.addWidget(self.spin_max_holdings, 1, 3)
        
        group_risk.setLayout(risk_layout)
        layout.addWidget(group_risk)
        
        # 프리셋
        group_preset = QGroupBox("📋 전략 프리셋")
        preset_layout = QHBoxLayout()
        
        btn_aggressive = QPushButton("🔥 공격적")
        btn_aggressive.clicked.connect(lambda: self.apply_preset("aggressive"))
        btn_normal = QPushButton("⚖️ 표준")
        btn_normal.clicked.connect(lambda: self.apply_preset("normal"))
        btn_conservative = QPushButton("🛡️ 보수적")
        btn_conservative.clicked.connect(lambda: self.apply_preset("conservative"))
        
        preset_layout.addWidget(btn_aggressive)
        preset_layout.addWidget(btn_normal)
        preset_layout.addWidget(btn_conservative)
        group_preset.setLayout(preset_layout)
        layout.addWidget(group_preset)
        
        layout.addStretch(1)
        return widget

    def create_statistics_tab(self):
        """거래 통계 탭"""
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        stat_style = """
            QLabel {
                background-color: #16213e;
                border: 1px solid #3d5a80;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
            }
        """
        
        self.stat_trades = QLabel("📊 총 거래 횟수\n0 회")
        self.stat_trades.setStyleSheet(stat_style)
        self.stat_trades.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stat_trades, 0, 0)
        
        self.stat_winrate = QLabel("🎯 승률\n0.0 %")
        self.stat_winrate.setStyleSheet(stat_style)
        self.stat_winrate.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stat_winrate, 0, 1)
        
        self.stat_profit = QLabel("💰 총 실현손익\n0 원")
        self.stat_profit.setStyleSheet(stat_style)
        self.stat_profit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stat_profit, 0, 2)
        
        self.stat_holdings = QLabel("📦 보유 종목\n0 개")
        self.stat_holdings.setStyleSheet(stat_style)
        self.stat_holdings.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stat_holdings, 0, 3)
        
        btn_reset = QPushButton("🔄 통계 초기화")
        btn_reset.clicked.connect(self.reset_statistics)
        layout.addWidget(btn_reset, 1, 0, 1, 4)
        
        layout.setRowStretch(2, 1)
        return widget

    def create_splitter(self):
        """스플리터 생성"""
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 포트폴리오 테이블
        self.table = QTableWidget()
        cols = ["코인명", "현재가", "목표가", "MA(5)", "상태", "보유수량", "매입가", "수익률", "최고수익률", "투자금"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        # 로그 창
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(180)
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("로그가 여기에 표시됩니다...")
        
        splitter.addWidget(self.table)
        splitter.addWidget(self.log_text)
        splitter.setSizes([500, 180])
        return splitter

    def create_statusbar(self):
        """상태바 생성"""
        self.statusbar = self.statusBar()
        
        self.status_time = QLabel()
        self.statusbar.addWidget(self.status_time)
        self.statusbar.addWidget(QLabel(" | "))
        
        self.status_trading = QLabel("● 대기 중")
        self.status_trading.setStyleSheet("color: #ffc107;")
        self.statusbar.addWidget(self.status_trading)
        
        self.statusbar.addWidget(QLabel(" | "))
        self.status_realtime = QLabel("실시간: 비활성")
        self.statusbar.addWidget(self.status_realtime)
        
        self.statusbar.addPermanentWidget(QLabel("Upbit Pro Algo-Trader v1.0"))

    def setup_timers(self):
        """타이머 설정"""
        self.timer_monitor = QTimer(self)
        self.timer_monitor.start(1000)
        self.timer_monitor.timeout.connect(self.on_timer_tick)

    def on_timer_tick(self):
        """1초마다 실행"""
        now = datetime.datetime.now()
        self.status_time.setText(now.strftime("%Y-%m-%d %H:%M:%S"))

    # ------------------------------------------------------------------
    # 설정 저장/불러오기
    # ------------------------------------------------------------------
    def save_settings(self):
        """설정 저장"""
        settings = {
            "coins": self.input_coins.text(),
            "candle": self.combo_candle.currentText(),
            "betting_ratio": self.spin_betting.value(),
            "k_value": self.spin_k.value(),
            "ts_start": self.spin_ts_start.value(),
            "ts_stop": self.spin_ts_stop.value(),
            "loss_cut": self.spin_loss.value(),
            "use_rsi": self.chk_use_rsi.isChecked(),
            "rsi_upper": self.spin_rsi_upper.value(),
            "rsi_period": self.spin_rsi_period.value(),
            "use_volume": self.chk_use_volume.isChecked(),
            "volume_mult": self.spin_volume_mult.value(),
            "use_risk": self.chk_use_risk.isChecked(),
            "max_daily_loss": self.spin_max_loss.value(),
            "max_holdings": self.spin_max_holdings.value()
        }
        
        try:
            with open(Config.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            self.log("✅ 설정이 저장되었습니다")
        except Exception as e:
            self.log(f"[ERROR] 설정 저장 실패: {e}")

    def load_settings(self):
        """설정 불러오기"""
        try:
            if os.path.exists(Config.SETTINGS_FILE):
                with open(Config.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    s = json.load(f)
                
                self.input_coins.setText(s.get("coins", Config.DEFAULT_COINS))
                self.combo_candle.setCurrentText(s.get("candle", Config.DEFAULT_CANDLE))
                self.spin_betting.setValue(s.get("betting_ratio", Config.DEFAULT_BETTING_RATIO))
                self.spin_k.setValue(s.get("k_value", Config.DEFAULT_K_VALUE))
                self.spin_ts_start.setValue(s.get("ts_start", Config.DEFAULT_TS_START))
                self.spin_ts_stop.setValue(s.get("ts_stop", Config.DEFAULT_TS_STOP))
                self.spin_loss.setValue(s.get("loss_cut", Config.DEFAULT_LOSS_CUT))
                self.chk_use_rsi.setChecked(s.get("use_rsi", Config.DEFAULT_USE_RSI))
                self.spin_rsi_upper.setValue(s.get("rsi_upper", Config.DEFAULT_RSI_UPPER))
                self.spin_rsi_period.setValue(s.get("rsi_period", Config.DEFAULT_RSI_PERIOD))
                self.chk_use_volume.setChecked(s.get("use_volume", Config.DEFAULT_USE_VOLUME))
                self.spin_volume_mult.setValue(s.get("volume_mult", Config.DEFAULT_VOLUME_MULTIPLIER))
                self.chk_use_risk.setChecked(s.get("use_risk", Config.DEFAULT_USE_RISK_MGMT))
                self.spin_max_loss.setValue(s.get("max_daily_loss", Config.DEFAULT_MAX_DAILY_LOSS))
                self.spin_max_holdings.setValue(s.get("max_holdings", Config.DEFAULT_MAX_HOLDINGS))
                
                self.log("📂 저장된 설정을 불러왔습니다")
        except Exception as e:
            self.log(f"[WARN] 설정 불러오기 실패: {e}")

    # ------------------------------------------------------------------
    # 로그인 및 잔고
    # ------------------------------------------------------------------
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
            self.balance = self.upbit.get_balance("KRW")
            self.lbl_balance.setText(f"💰 주문가능금액: {self.balance:,.0f} 원")
        except Exception as e:
            self.logger.error(f"잔고 조회 실패: {e}")

    # ------------------------------------------------------------------
    # 매매 시작/중지
    # ------------------------------------------------------------------
    def start_trading(self):
        """매매 시작"""
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
        
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_trading.setText("● 분석 중")
        self.status_trading.setStyleSheet("color: #00b4d8;")
        
        candle_interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
        
        for coin in coins:
            try:
                # 목표가 및 MA 계산
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
                
                self.log(f"[{coin}] 목표가:{target_price:,.0f}, MA5:{ma5:,.0f}")
                
            except Exception as e:
                self.log(f"[ERROR] {coin} 초기화 실패: {e}")
                self.logger.error(f"{coin} 초기화 실패: {e}")
        
        if self.universe:
            # 가격 모니터링 시작
            self.price_thread.set_coins(list(self.universe.keys()))
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
        """RSI 계산"""
        try:
            interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=period+2)
            if df is None or len(df) < period + 1:
                return 50
            
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = (-delta).where(delta < 0, 0)
            
            avg_gain = gain.rolling(window=period).mean().iloc[-1]
            avg_loss = loss.rolling(window=period).mean().iloc[-1]
            
            if avg_loss == 0:
                return 100
            
            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))
        except Exception as e:
            return 50

    # ------------------------------------------------------------------
    # 가격 업데이트 및 조건 확인
    # ------------------------------------------------------------------
    def on_price_update(self, prices):
        """실시간 가격 업데이트"""
        if not self.is_running:
            return
        
        for ticker, price in prices.items():
            if ticker not in self.universe:
                continue
            
            info = self.universe[ticker]
            info['current'] = price
            
            # 현재가 UI 업데이트
            self.table.setItem(info['row'], 1, QTableWidgetItem(f"{price:,.0f}"))
            
            # 매수 로직
            if info['state'] == '감시중' and info['qty'] == 0:
                self._check_buy_condition(ticker, price, info)
            
            # 매도 로직
            elif info['state'] == '보유중' and info['qty'] > 0:
                self._check_sell_condition(ticker, price, info)

    def _check_buy_condition(self, ticker, curr, info):
        """매수 조건 확인"""
        # 1. 목표가 돌파
        if curr < info['target']:
            return
        
        # 2. MA5 위
        if curr < info['ma5']:
            return
        
        # 3. RSI 필터
        if self.chk_use_rsi.isChecked():
            rsi = self.calculate_rsi(ticker, self.spin_rsi_period.value())
            if rsi >= self.spin_rsi_upper.value():
                self.log(f"[{ticker}] RSI {rsi:.1f} >= {self.spin_rsi_upper.value()} (과매수) 진입 보류")
                return
        
        # 4. 리스크 관리
        if not self.check_risk_limits():
            return
        
        # 매수 실행
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
        profit_item = QTableWidgetItem(f"{profit_rate:.2f}%")
        if profit_rate >= 0:
            profit_item.setForeground(QColor("#e63946"))
        else:
            profit_item.setForeground(QColor("#4361ee"))
        self.table.setItem(row, 7, profit_item)
        self.table.setItem(row, 8, QTableWidgetItem(f"{info['max_profit_rate']:.2f}%"))
        
        # 1. 손절
        loss_limit = -self.spin_loss.value()
        if profit_rate <= loss_limit:
            self.log(f"🛑 [{ticker}] 손절 조건 ({profit_rate:.2f}%) → 매도")
            self.execute_sell(ticker, "손절")
            return
        
        # 2. 트레일링 스톱
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
        
        ratio = self.spin_betting.value() / 100
        bet_cash = self.balance * ratio
        
        if bet_cash < 5000:  # 업비트 최소 주문금액
            self.log(f"[{ticker}] 매수금액 부족 (최소 5,000원)")
            return
        
        try:
            # 시장가 매수
            result = self.upbit.buy_market_order(ticker, bet_cash)
            
            if result and 'uuid' in result:
                info = self.universe[ticker]
                info['state'] = '주문중'
                self.set_table_item(info['row'], 4, "⏳ 주문중", "#ffc107")
                
                self.log(f"📤 [{ticker}] 매수 주문: {bet_cash:,.0f}원")
                self.logger.info(f"매수 주문: {ticker} {bet_cash:,.0f}원")
                
                # 체결 확인
                QTimer.singleShot(2000, lambda: self.check_buy_execution(ticker, result['uuid']))
            else:
                self.log(f"[ERROR] 매수 주문 실패: {result}")
                
        except Exception as e:
            self.log(f"[ERROR] 매수 주문 실패: {e}")
            self.logger.error(f"매수 주문 실패 ({ticker}): {e}")

    def check_buy_execution(self, ticker, uuid):
        """매수 체결 확인"""
        try:
            order = self.upbit.get_order(uuid)
            if order and order.get('state') == 'done':
                info = self.universe[ticker]
                
                # 체결 정보
                executed_volume = float(order.get('executed_volume', 0))
                paid_fee = float(order.get('paid_fee', 0))
                total_price = float(order.get('price', 0)) + paid_fee
                
                if executed_volume > 0:
                    avg_price = total_price / executed_volume
                    
                    info['qty'] = executed_volume
                    info['buy_price'] = avg_price
                    info['invest_amt'] = total_price
                    info['high_since_buy'] = avg_price
                    info['state'] = '보유중'
                    
                    row = info['row']
                    self.table.setItem(row, 5, QTableWidgetItem(f"{executed_volume:.8f}"))
                    self.table.setItem(row, 6, QTableWidgetItem(f"{avg_price:,.0f}"))
                    self.table.setItem(row, 9, QTableWidgetItem(f"{total_price:,.0f}"))
                    self.set_table_item(row, 4, "💼 보유중", "#00b4d8")
                    
                    self.log(f"✅ [{ticker}] 매수 체결: {executed_volume:.8f} @ {avg_price:,.0f}원")
                    self.get_balance()
            else:
                # 아직 체결 안됨, 다시 확인
                QTimer.singleShot(2000, lambda: self.check_buy_execution(ticker, uuid))
        except Exception as e:
            self.logger.error(f"체결 확인 실패 ({ticker}): {e}")

    def execute_sell(self, ticker, reason):
        """매도 주문"""
        if not self.upbit:
            return
        
        info = self.universe[ticker]
        qty = info['qty']
        if qty == 0:
            return
        
        try:
            result = self.upbit.sell_market_order(ticker, qty)
            
            if result and 'uuid' in result:
                self.log(f"📤 [{ticker}] 매도 주문: {qty:.8f} ({reason})")
                self.logger.info(f"매도 주문: {ticker} {qty:.8f} ({reason})")
                
                QTimer.singleShot(2000, lambda: self.check_sell_execution(ticker, result['uuid'], reason))
            else:
                self.log(f"[ERROR] 매도 주문 실패: {result}")
                
        except Exception as e:
            self.log(f"[ERROR] 매도 주문 실패: {e}")
            self.logger.error(f"매도 주문 실패 ({ticker}): {e}")

    def check_sell_execution(self, ticker, uuid, reason):
        """매도 체결 확인"""
        try:
            order = self.upbit.get_order(uuid)
            if order and order.get('state') == 'done':
                info = self.universe[ticker]
                
                executed_volume = float(order.get('executed_volume', 0))
                trades_price = float(order.get('trades', [{}])[0].get('price', 0)) if order.get('trades') else 0
                
                # 손익 계산
                sell_amount = executed_volume * trades_price
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
                self.set_table_item(info['row'], 4, "✅ 청산완료", "#6c757d")
                
                self.log(f"✅ [{ticker}] 매도 체결 (손익: {profit:+,.0f}원)")
                self._update_statistics()
                self.get_balance()
            else:
                QTimer.singleShot(2000, lambda: self.check_sell_execution(ticker, uuid, reason))
        except Exception as e:
            self.logger.error(f"매도 체결 확인 실패 ({ticker}): {e}")

    # ------------------------------------------------------------------
    # 유틸리티
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
        presets = {
            "aggressive": {"k": 0.5, "ts_start": 3.0, "ts_stop": 1.5, "loss": 5.0},
            "normal": {"k": 0.4, "ts_start": 5.0, "ts_stop": 2.0, "loss": 3.0},
            "conservative": {"k": 0.3, "ts_start": 7.0, "ts_stop": 2.5, "loss": 2.0}
        }
        
        if preset_type in presets:
            p = presets[preset_type]
            self.spin_k.setValue(p["k"])
            self.spin_ts_start.setValue(p["ts_start"])
            self.spin_ts_stop.setValue(p["ts_stop"])
            self.spin_loss.setValue(p["loss"])
            self.log(f"📋 {preset_type.upper()} 프리셋 적용됨")

    def set_table_item(self, row, col, text, bg_color):
        """테이블 아이템 설정"""
        item = QTableWidgetItem(text)
        item.setBackground(QColor(bg_color))
        item.setForeground(QColor("#1a1a2e"))
        self.table.setItem(row, col, item)

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
        """로그 출력"""
        t = datetime.datetime.now().strftime("[%H:%M:%S]")
        self.log_text.append(f"{t} {msg}")
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def closeEvent(self, event):
        """종료 처리"""
        if self.is_running:
            reply = QMessageBox.question(self, "종료 확인",
                "매매가 진행 중입니다. 정말 종료하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        self.price_thread.stop()
        self.price_thread.wait()
        self.logger.info("프로그램 종료")
        event.accept()


# ============================================================================
# 메인 실행
# ============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    trader = UpbitProTrader()
    trader.show()
    
    sys.exit(app.exec())
