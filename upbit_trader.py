"""
Upbit Pro Algo-Trader v2.0
업비트 OpenAPI 기반 자동매매 프로그램

변동성 돌파 전략 + 이동평균 필터 + 트레일링 스톱
24시간 코인 마켓 최적화

v2.0 신규 기능:
- 사용자 정의 프리셋 관리
- 시스템 트레이 통합
- Windows 자동 시작
- 인앱 도움말 및 가이드
- 향상된 UI/UX
"""

import sys
import os
import json
import datetime
import time
import logging
import threading
from pathlib import Path
import winreg
import pandas as pd

try:
    import pyupbit
except ImportError:
    print("pyupbit 라이브러리가 필요합니다. 'pip install pyupbit' 명령으로 설치해주세요.")
    sys.exit(1)

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import QColor, QFont, QAction, QIcon


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
    
    # MACD 설정
    DEFAULT_MACD_FAST = 12
    DEFAULT_MACD_SLOW = 26
    DEFAULT_MACD_SIGNAL = 9
    DEFAULT_USE_MACD = True
    
    # 볼린저 밴드 설정
    DEFAULT_BB_PERIOD = 20
    DEFAULT_BB_STD = 2.0
    DEFAULT_USE_BB = False
    
    # ATR 설정 (동적 손절용)
    DEFAULT_ATR_PERIOD = 14
    DEFAULT_ATR_MULTIPLIER = 2.0
    DEFAULT_USE_ATR = False
    
    # 거래량 설정
    DEFAULT_VOLUME_MULTIPLIER = 1.5
    DEFAULT_VOLUME_PERIOD = 20
    DEFAULT_USE_VOLUME = True
    
    # 부분 익절 설정
    DEFAULT_PARTIAL_PROFIT_1 = 5.0   # 1차 익절 수익률
    DEFAULT_PARTIAL_RATIO_1 = 50.0   # 1차 익절 비율 (%)
    DEFAULT_PARTIAL_PROFIT_2 = 10.0  # 2차 익절 수익률
    DEFAULT_USE_PARTIAL = False
    
    # 리스크 관리
    DEFAULT_MAX_DAILY_LOSS = 5.0
    DEFAULT_MAX_HOLDINGS = 5
    DEFAULT_USE_RISK_MGMT = True
    
    # 파일 경로
    SETTINGS_FILE = "upbit_settings.json"
    PRESETS_FILE = "upbit_presets.json"
    LOG_DIR = "logs"
    
    # 가격 갱신 주기 (초)
    PRICE_UPDATE_INTERVAL = 1
    
    # 기본 프리셋 정의
    DEFAULT_PRESETS = {
        "aggressive": {
            "name": "🔥 공격적",
            "description": "높은 수익을 추구하지만 리스크도 높음",
            "k": 0.5, "ts_start": 3.0, "ts_stop": 1.5, "loss": 5.0,
            "betting": 15.0, "rsi_upper": 75, "max_holdings": 7
        },
        "normal": {
            "name": "⚖️ 표준",
            "description": "균형 잡힌 수익과 리스크 관리",
            "k": 0.4, "ts_start": 5.0, "ts_stop": 2.0, "loss": 3.0,
            "betting": 10.0, "rsi_upper": 70, "max_holdings": 5
        },
        "conservative": {
            "name": "🛡️ 보수적",
            "description": "안정적인 수익, 낮은 리스크",
            "k": 0.3, "ts_start": 7.0, "ts_stop": 2.5, "loss": 2.0,
            "betting": 5.0, "rsi_upper": 65, "max_holdings": 3
        }
    }
    
    # 툴팁 설명
    TOOLTIPS = {
        "coins": "감시할 코인 목록을 콤마(,)로 구분하여 입력합니다.\n예: KRW-BTC,KRW-ETH,KRW-XRP\n\n💡 팁: 변동성이 큰 코인이 전략에 더 적합합니다.",
        "candle": "변동성 계산에 사용할 캔들 간격입니다.\n\n• 1분~30분: 단타 트레이딩 (잦은 거래)\n• 1시간~4시간: 스윙 트레이딩 (권장)\n• 일봉: 장기 트레이딩",
        "betting": "총 잔고 대비 종목당 투자 비율입니다.\n\n권장 범위: 5% ~ 20%\n⚠️ 높을수록 수익/손실 폭이 커집니다.",
        "k_value": "변동성 돌파 계수 (래리 윌리엄스 전략)\n\n목표가 = 시가 + (전일 변동폭 × K값)\n\n• 낮을수록 (0.3): 보수적, 진입 빈번\n• 높을수록 (0.6): 공격적, 진입 엄격\n\n권장: 0.3 ~ 0.5",
        "ts_start": "트레일링 스톱이 발동되는 수익률입니다.\n\n이 수익률에 도달하면 고점 추적을 시작합니다.\n권장: 3% ~ 10%",
        "ts_stop": "고점 대비 하락 허용폭입니다.\n\n고점에서 이 비율만큼 하락하면 매도합니다.\n권장: 1% ~ 3%",
        "loss_cut": "절대 손절 기준입니다.\n\n매수가 대비 이 비율만큼 하락하면 즉시 매도합니다.\n권장: 2% ~ 5%",
        "rsi": "RSI(상대강도지수)가 이 값 이상이면 과매수로 판단하여\n매수를 보류합니다.\n\n권장: 65 ~ 75",
        "rsi_period": "RSI 계산에 사용할 캔들 수입니다.\n\n일반적으로 14를 사용합니다.\n권장: 10 ~ 20",
        "volume": "평균 거래량 대비 배수입니다.\n\n현재 거래량이 평균의 이 배수 이상이어야 매수합니다.\n권장: 1.2 ~ 2.0",
        "max_loss": "하루 최대 허용 손실률입니다.\n\n이 손실에 도달하면 당일 신규 매수가 중지됩니다.\n권장: 3% ~ 10%",
        "max_holdings": "동시에 보유할 수 있는 최대 종목 수입니다.\n\n분산 투자로 리스크를 관리합니다.\n권장: 3 ~ 7개"
    }
    
    # 도움말 콘텐츠
    HELP_CONTENT = {
        "quick_start": """
## 🚀 빠른 시작 가이드

### 1단계: API 키 설정
1. [업비트 OpenAPI 관리](https://upbit.com/mypage/open_api_management) 페이지에서 API 키를 발급받습니다.
2. **주문** 권한을 포함해야 합니다.
3. Access Key와 Secret Key를 프로그램에 입력합니다.
4. "🔌 시스템 접속" 버튼을 클릭합니다.

### 2단계: 코인 선택
감시할 코인을 콤마로 구분하여 입력합니다.
예: `KRW-BTC,KRW-ETH,KRW-XRP`

### 3단계: 전략 선택
- 초보자: **보수적** 프리셋 권장
- 경험자: **표준** 프리셋으로 시작
- 고급: 직접 파라미터 조정

### 4단계: 매매 시작
"🚀 전략 분석 및 매매 시작" 버튼을 클릭합니다.
        """,
        "strategy": """
## 📈 전략 설명

### 변동성 돌파 전략
래리 윌리엄스(Larry Williams)가 개발한 단기 트레이딩 전략입니다.

**핵심 원리:**
- 전일 고가 - 전일 저가 = 변동폭
- 목표가 = 당일 시가 + (변동폭 × K값)
- 현재가가 목표가를 돌파하면 매수

### MA5 추세 필터
5봉 이동평균선 위에서만 매수하여 상승 추세를 확인합니다.

### RSI 과매수 필터
RSI가 설정값 이상이면 과매수 구간으로 판단하여 진입을 보류합니다.

### 트레일링 스톱
- 목표 수익률 도달 시 고점 추적 시작
- 고점 대비 설정 하락폭 발생 시 매도
- 수익을 보존하면서 추가 상승 여지 확보

### 손절
매수가 대비 설정 손실률 도달 시 즉시 매도하여 손실을 제한합니다.
        """,
        "faq": """
## ❓ 자주 묻는 질문

**Q: API 키는 안전한가요?**
A: API 키는 로컬에만 저장되며 외부로 전송되지 않습니다.

**Q: 프로그램을 종료해도 되나요?**
A: 프로그램 종료 시 자동매매도 중지됩니다. 24시간 운영을 원하면 프로그램을 계속 실행해야 합니다.

**Q: 손실이 발생하면 어떻게 되나요?**
A: 설정된 손절률에 따라 자동으로 매도됩니다. 일일 최대 손실에 도달하면 신규 매수가 중지됩니다.

**Q: 어떤 프리셋을 선택해야 하나요?**
A: 처음 사용자는 "보수적" 프리셋으로 시작하여 프로그램에 익숙해진 후 조정하는 것을 권장합니다.

**Q: 여러 코인을 동시에 거래할 수 있나요?**
A: 네, 콤마로 구분하여 여러 코인을 입력할 수 있습니다. 최대 보유 종목 설정으로 분산 투자가 가능합니다.
        """
    }


# ============================================================================
# 다크 테마 스타일시트
# ============================================================================
DARK_STYLESHEET = """
/* ============================================= */
/* 기본 위젯 스타일 */
/* ============================================= */
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #edf2f4;
    font-family: '맑은 고딕', 'Malgun Gothic', 'Segoe UI', sans-serif;
    font-size: 13px;
}

QDialog {
    background-color: #1a1a2e;
    font-family: '맑은 고딕', 'Malgun Gothic', sans-serif;
}

/* ============================================= */
/* 그룹박스 */
/* ============================================= */
QGroupBox {
    border: 1px solid #3d5a80;
    border-radius: 8px;
    margin-top: 16px;
    padding: 20px 15px 15px 15px;
    font-weight: bold;
    font-size: 14px;
    color: #90e0ef;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 10px;
    background-color: #1a1a2e;
}

/* ============================================= */
/* 버튼 */
/* ============================================= */
QPushButton {
    background-color: #3d5a80;
    color: #edf2f4;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: bold;
    font-size: 13px;
    min-height: 20px;
}

QPushButton:hover { background-color: #4a6fa5; }
QPushButton:pressed { background-color: #2c4a6e; }
QPushButton:disabled { background-color: #2d2d44; color: #666680; }

QPushButton#loginBtn { background-color: #00b4d8; }
QPushButton#loginBtn:hover { background-color: #0096c7; }
QPushButton#startBtn { background-color: #e63946; font-size: 15px; padding: 12px 25px; }
QPushButton#startBtn:hover { background-color: #d62839; }
QPushButton#stopBtn { background-color: #6c757d; }

/* ============================================= */
/* 체크박스 */
/* ============================================= */
QCheckBox {
    spacing: 10px;
    font-size: 13px;
    color: #edf2f4;
    padding: 5px;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid #3d5a80;
    background-color: #16213e;
}

QCheckBox::indicator:checked {
    background-color: #00b4d8;
    border: 2px solid #00b4d8;
    image: none;
}

QCheckBox::indicator:checked:after {
    content: "✓";
}

QCheckBox::indicator:hover {
    border: 2px solid #00b4d8;
}

QCheckBox:disabled {
    color: #666680;
}

/* ============================================= */
/* 입력 필드 */
/* ============================================= */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #16213e;
    border: 1px solid #3d5a80;
    border-radius: 5px;
    padding: 10px;
    color: #edf2f4;
    font-size: 13px;
    selection-background-color: #00b4d8;
    min-height: 18px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #00b4d8;
}

QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #90e0ef;
}

/* ============================================= */
/* 테이블 */
/* ============================================= */
QTableWidget {
    background-color: #16213e;
    alternate-background-color: #1a2744;
    gridline-color: #2d3a5a;
    border: 1px solid #3d5a80;
    border-radius: 8px;
    color: #edf2f4;
    font-size: 12px;
}

QTableWidget::item { 
    padding: 10px; 
    border-bottom: 1px solid #2d3a5a; 
}
QTableWidget::item:selected { background-color: #3d5a80; }

QHeaderView::section {
    background-color: #0f3460;
    color: #90e0ef;
    padding: 12px;
    border: none;
    border-bottom: 2px solid #00b4d8;
    font-weight: bold;
    font-size: 12px;
}

/* ============================================= */
/* 텍스트 영역 */
/* ============================================= */
QTextEdit {
    background-color: #0d1b2a;
    border: 1px solid #3d5a80;
    border-radius: 8px;
    color: #90e0ef;
    font-family: 'Consolas', 'D2Coding', monospace;
    font-size: 12px;
    padding: 12px;
    line-height: 1.4;
}

/* ============================================= */
/* 레이블 */
/* ============================================= */
QLabel { 
    color: #b8c5d6; 
    font-size: 13px; 
}
QLabel#depositLabel { color: #00b4d8; font-weight: bold; font-size: 15px; }
QLabel#profitLabel { color: #f72585; font-weight: bold; font-size: 15px; }

/* ============================================= */
/* 상태바 */
/* ============================================= */
QStatusBar {
    background-color: #0f3460;
    color: #90e0ef;
    border-top: 1px solid #3d5a80;
    font-size: 12px;
    padding: 5px;
}

/* ============================================= */
/* 탭 위젯 */
/* ============================================= */
QTabWidget::pane { 
    border: 1px solid #3d5a80; 
    border-radius: 8px; 
    background-color: #1a1a2e; 
    padding: 5px;
}
QTabBar::tab {
    background-color: #16213e;
    color: #b8c5d6;
    padding: 12px 25px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 13px;
}
QTabBar::tab:selected { background-color: #3d5a80; color: #edf2f4; font-weight: bold; }
QTabBar::tab:hover:!selected { background-color: #2d3a5a; }

/* ============================================= */
/* 리스트 위젯 */
/* ============================================= */
QListWidget {
    background-color: #16213e;
    border: 1px solid #3d5a80;
    border-radius: 6px;
    padding: 5px;
    font-size: 13px;
}

QListWidget::item {
    padding: 10px;
    border-radius: 4px;
    margin: 2px;
}

QListWidget::item:selected {
    background-color: #3d5a80;
    color: #edf2f4;
}

QListWidget::item:hover:!selected {
    background-color: #2d3a5a;
}

/* ============================================= */
/* 스크롤바 */
/* ============================================= */
QScrollBar:vertical {
    background-color: #16213e;
    width: 12px;
    border-radius: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #3d5a80;
    border-radius: 6px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #4a6fa5;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ============================================= */
/* 메뉴바 */
/* ============================================= */
QMenuBar {
    background-color: #0f3460;
    color: #edf2f4;
    padding: 5px;
    font-size: 13px;
}

QMenuBar::item {
    padding: 8px 15px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #3d5a80;
}

QMenu {
    background-color: #16213e;
    border: 1px solid #3d5a80;
    border-radius: 6px;
    padding: 5px;
}

QMenu::item {
    padding: 10px 30px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #3d5a80;
}

/* ============================================= */
/* 툴팁 */
/* ============================================= */
QToolTip {
    background-color: #0f3460;
    color: #edf2f4;
    border: 1px solid #3d5a80;
    border-radius: 6px;
    padding: 10px;
    font-size: 12px;
}
"""


# ============================================================================
# 프리셋 관리 다이얼로그
# ============================================================================
class PresetManagerDialog(QDialog):
    """사용자 정의 프리셋 관리 다이얼로그"""
    
    def __init__(self, parent=None, current_values=None):
        super().__init__(parent)
        self.current_values = current_values or {}
        self.presets = self.load_presets()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("📋 프리셋 관리")
        self.setFixedSize(700, 600)
        self.setStyleSheet(DARK_STYLESHEET)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 프리셋 목록
        group_list = QGroupBox("저장된 프리셋")
        list_layout = QVBoxLayout()
        
        self.preset_list = QListWidget()
        self.preset_list.itemClicked.connect(self.on_preset_selected)
        self.refresh_preset_list()
        list_layout.addWidget(self.preset_list)
        
        # 프리셋 상세 정보
        self.detail_label = QLabel("프리셋을 선택하면 상세 정보가 표시됩니다.")
        self.detail_label.setStyleSheet("padding: 10px; background-color: #16213e; border-radius: 5px;")
        self.detail_label.setWordWrap(True)
        list_layout.addWidget(self.detail_label)
        
        group_list.setLayout(list_layout)
        layout.addWidget(group_list)
        
        # 새 프리셋 생성
        group_new = QGroupBox("새 프리셋 저장")
        new_layout = QHBoxLayout()
        
        new_layout.addWidget(QLabel("이름:"))
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("프리셋 이름 입력")
        new_layout.addWidget(self.input_name)
        
        btn_save = QPushButton("💾 현재 설정 저장")
        btn_save.clicked.connect(self.save_current_preset)
        new_layout.addWidget(btn_save)
        
        group_new.setLayout(new_layout)
        layout.addWidget(group_new)
        
        # 버튼 영역
        btn_layout = QHBoxLayout()
        
        btn_delete = QPushButton("🗑️ 선택 삭제")
        btn_delete.clicked.connect(self.delete_preset)
        btn_layout.addWidget(btn_delete)
        
        btn_layout.addStretch(1)
        
        btn_apply = QPushButton("✅ 선택 적용")
        btn_apply.clicked.connect(self.apply_preset)
        btn_layout.addWidget(btn_apply)
        
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
    
    def load_presets(self):
        """프리셋 파일 로드"""
        presets = dict(Config.DEFAULT_PRESETS)  # 기본 프리셋 복사
        try:
            if os.path.exists(Config.PRESETS_FILE):
                with open(Config.PRESETS_FILE, 'r', encoding='utf-8') as f:
                    user_presets = json.load(f)
                    presets.update(user_presets)
        except Exception:
            pass
        return presets
    
    def save_presets_to_file(self):
        """사용자 프리셋만 파일에 저장"""
        user_presets = {k: v for k, v in self.presets.items() 
                       if k not in Config.DEFAULT_PRESETS}
        try:
            with open(Config.PRESETS_FILE, 'w', encoding='utf-8') as f:
                json.dump(user_presets, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def refresh_preset_list(self):
        """프리셋 목록 갱신"""
        self.preset_list.clear()
        for key, preset in self.presets.items():
            name = preset.get('name', key)
            is_default = key in Config.DEFAULT_PRESETS
            prefix = "[기본] " if is_default else "[사용자] "
            item = QListWidgetItem(prefix + name)
            item.setData(Qt.ItemDataRole.UserRole, key)
            if is_default:
                item.setForeground(QColor("#90e0ef"))
            else:
                item.setForeground(QColor("#f72585"))
            self.preset_list.addItem(item)
    
    def on_preset_selected(self, item):
        """프리셋 선택 시 상세 정보 표시"""
        key = item.data(Qt.ItemDataRole.UserRole)
        preset = self.presets.get(key, {})
        
        desc = preset.get('description', '설명 없음')
        details = f"""<b>{preset.get('name', key)}</b><br><br>
{desc}<br><br>
<b>설정값:</b><br>
• K값: {preset.get('k', '-')}<br>
• TS 발동: {preset.get('ts_start', '-')}%<br>
• TS 하락폭: {preset.get('ts_stop', '-')}%<br>
• 손절률: {preset.get('loss', '-')}%<br>
• 투자비중: {preset.get('betting', '-')}%<br>
• RSI 상한: {preset.get('rsi_upper', '-')}<br>
• 최대 보유: {preset.get('max_holdings', '-')}개
"""
        self.detail_label.setText(details)
    
    def save_current_preset(self):
        """현재 설정을 새 프리셋으로 저장"""
        name = self.input_name.text().strip()
        if not name:
            QMessageBox.warning(self, "경고", "프리셋 이름을 입력해주세요.")
            return
        
        # 키 생성 (공백 제거, 소문자)
        key = "custom_" + name.replace(" ", "_").lower()
        
        if key in Config.DEFAULT_PRESETS:
            QMessageBox.warning(self, "경고", "기본 프리셋과 같은 이름은 사용할 수 없습니다.")
            return
        
        self.presets[key] = {
            "name": "⭐ " + name,
            "description": f"사용자 정의 프리셋 ({datetime.datetime.now().strftime('%Y-%m-%d')})",
            **self.current_values
        }
        
        self.save_presets_to_file()
        self.refresh_preset_list()
        self.input_name.clear()
        QMessageBox.information(self, "완료", f"'{name}' 프리셋이 저장되었습니다.")
    
    def delete_preset(self):
        """선택된 프리셋 삭제"""
        item = self.preset_list.currentItem()
        if not item:
            return
        
        key = item.data(Qt.ItemDataRole.UserRole)
        if key in Config.DEFAULT_PRESETS:
            QMessageBox.warning(self, "경고", "기본 프리셋은 삭제할 수 없습니다.")
            return
        
        reply = QMessageBox.question(self, "확인", 
            f"'{self.presets[key].get('name', key)}' 프리셋을 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.presets[key]
            self.save_presets_to_file()
            self.refresh_preset_list()
            self.detail_label.setText("프리셋을 선택하면 상세 정보가 표시됩니다.")
    
    def apply_preset(self):
        """선택된 프리셋 적용"""
        item = self.preset_list.currentItem()
        if not item:
            QMessageBox.warning(self, "경고", "적용할 프리셋을 선택해주세요.")
            return
        
        key = item.data(Qt.ItemDataRole.UserRole)
        self.selected_preset = self.presets.get(key)
        self.accept()
    
    def get_selected_preset(self):
        return getattr(self, 'selected_preset', None)


# ============================================================================
# 도움말 다이얼로그
# ============================================================================
class HelpDialog(QDialog):
    """인앱 도움말 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("📚 도움말")
        self.setFixedSize(800, 700)
        self.setStyleSheet(DARK_STYLESHEET)
        
        layout = QVBoxLayout(self)
        
        # 탭 위젯
        tabs = QTabWidget()
        
        # 빠른 시작 탭
        self.quick_start_text = QTextEdit()
        self.quick_start_text.setReadOnly(True)
        self.quick_start_text.setHtml(self.markdown_to_html(Config.HELP_CONTENT['quick_start']))
        tabs.addTab(self.quick_start_text, "🚀 빠른 시작")
        
        # 전략 설명 탭
        self.strategy_text = QTextEdit()
        self.strategy_text.setReadOnly(True)
        self.strategy_text.setHtml(self.markdown_to_html(Config.HELP_CONTENT['strategy']))
        tabs.addTab(self.strategy_text, "📈 전략 설명")
        
        # FAQ 탭
        self.faq_text = QTextEdit()
        self.faq_text.setReadOnly(True)
        self.faq_text.setHtml(self.markdown_to_html(Config.HELP_CONTENT['faq']))
        tabs.addTab(self.faq_text, "❓ FAQ")
        
        layout.addWidget(tabs)
        
        # 닫기 버튼
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)
    
    def markdown_to_html(self, md_text):
        """간단한 마크다운 → HTML 변환"""
        html = md_text.strip()
        # 헤더 변환
        html = html.replace("## ", "<h2>").replace("\n### ", "</h2>\n<h3>")
        html = html.replace("### ", "<h3>")
        # 굵게 변환
        import re
        html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html)
        # 리스트 변환
        html = html.replace("\n- ", "\n• ")
        # 코드 변환
        html = re.sub(r'`(.+?)`', r'<code style="background:#16213e;padding:2px 5px;border-radius:3px;">\1</code>', html)
        # 줄바꿈
        html = html.replace("\n\n", "</p><p>").replace("\n", "<br>")
        return f"<div style='font-size:13px;line-height:1.6;'><p>{html}</p></div>"


# ============================================================================
# 시스템 설정 다이얼로그
# ============================================================================
class SettingsDialog(QDialog):
    """시스템 설정 다이얼로그"""
    
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.settings = settings or {}
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("⚙️ 시스템 설정")
        self.setFixedSize(550, 480)
        self.setStyleSheet(DARK_STYLESHEET)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 시스템 트레이 설정
        group_tray = QGroupBox("🖥️ 시스템 트레이")
        tray_layout = QVBoxLayout()
        
        self.chk_minimize_to_tray = QCheckBox("닫기 버튼 클릭 시 트레이로 최소화")
        self.chk_minimize_to_tray.setChecked(self.settings.get('minimize_to_tray', True))
        tray_layout.addWidget(self.chk_minimize_to_tray)
        
        self.chk_show_tray_notifications = QCheckBox("거래 체결 시 트레이 알림 표시")
        self.chk_show_tray_notifications.setChecked(self.settings.get('show_tray_notifications', True))
        tray_layout.addWidget(self.chk_show_tray_notifications)
        
        group_tray.setLayout(tray_layout)
        layout.addWidget(group_tray)
        
        # 시작 설정
        group_startup = QGroupBox("🚀 시작 설정")
        startup_layout = QVBoxLayout()
        
        self.chk_run_at_startup = QCheckBox("Windows 시작 시 자동 실행")
        self.chk_run_at_startup.setChecked(self.settings.get('run_at_startup', False))
        startup_layout.addWidget(self.chk_run_at_startup)
        
        self.chk_start_minimized = QCheckBox("시작 시 트레이로 최소화")
        self.chk_start_minimized.setChecked(self.settings.get('start_minimized', False))
        startup_layout.addWidget(self.chk_start_minimized)
        
        self.chk_auto_connect = QCheckBox("시작 시 자동 API 연결")
        self.chk_auto_connect.setChecked(self.settings.get('auto_connect', False))
        startup_layout.addWidget(self.chk_auto_connect)
        
        group_startup.setLayout(startup_layout)
        layout.addWidget(group_startup)
        
        # 알림 설정
        group_notify = QGroupBox("🔔 알림 설정")
        notify_layout = QVBoxLayout()
        
        self.chk_sound_enabled = QCheckBox("거래 체결 시 소리 재생")
        self.chk_sound_enabled.setChecked(self.settings.get('sound_enabled', False))
        notify_layout.addWidget(self.chk_sound_enabled)
        
        group_notify.setLayout(notify_layout)
        layout.addWidget(group_notify)
        
        layout.addStretch(1)
        
        # 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        
        btn_save = QPushButton("💾 저장")
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_save)
        
        btn_cancel = QPushButton("취소")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
    
    def get_settings(self):
        return {
            'minimize_to_tray': self.chk_minimize_to_tray.isChecked(),
            'show_tray_notifications': self.chk_show_tray_notifications.isChecked(),
            'run_at_startup': self.chk_run_at_startup.isChecked(),
            'start_minimized': self.chk_start_minimized.isChecked(),
            'auto_connect': self.chk_auto_connect.isChecked(),
            'sound_enabled': self.chk_sound_enabled.isChecked()
        }


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
        
        # 시스템 설정 초기화
        self.system_settings = {
            'minimize_to_tray': True,
            'show_tray_notifications': True,
            'run_at_startup': False,
            'start_minimized': False,
            'auto_connect': False,
            'sound_enabled': False
        }
        
        # 가격 갱신 스레드
        self.price_thread = PriceUpdateThread()
        self.price_thread.price_updated.connect(self.on_price_update)
        
        # 로깅 설정
        self.setup_logging()
        
        # UI 초기화
        self.init_ui()
        
        # 메뉴바 설정
        self.create_menu_bar()
        
        # 시스템 트레이 설정
        self.setup_tray()
        
        # 타이머 설정
        self.setup_timers()
        
        # 설정 불러오기
        self.load_settings()
        
        # 처음 실행 확인
        self.check_first_run()
        
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
        self.setWindowTitle("Upbit Pro Algo-Trader v2.0 [24H 코인 자동매매]")
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
        self.input_coins.setToolTip(Config.TOOLTIPS['coins'])
        layout.addWidget(self.input_coins, 0, 1, 1, 5)
        
        # 캔들 간격
        layout.addWidget(QLabel("🕐 캔들 간격:"), 1, 0)
        self.combo_candle = QComboBox()
        self.combo_candle.addItems(Config.CANDLE_INTERVALS.keys())
        self.combo_candle.setCurrentText(Config.DEFAULT_CANDLE)
        self.combo_candle.setToolTip(Config.TOOLTIPS['candle'])
        layout.addWidget(self.combo_candle, 1, 1)
        
        # 투자 비중
        layout.addWidget(QLabel("💵 종목당 투자비중:"), 1, 2)
        self.spin_betting = QDoubleSpinBox()
        self.spin_betting.setRange(1, 100)
        self.spin_betting.setValue(Config.DEFAULT_BETTING_RATIO)
        self.spin_betting.setSuffix(" %")
        self.spin_betting.setToolTip(Config.TOOLTIPS['betting'])
        layout.addWidget(self.spin_betting, 1, 3)
        
        # K값
        layout.addWidget(QLabel("📐 변동성 K값:"), 1, 4)
        self.spin_k = QDoubleSpinBox()
        self.spin_k.setRange(0.1, 1.0)
        self.spin_k.setSingleStep(0.1)
        self.spin_k.setValue(Config.DEFAULT_K_VALUE)
        self.spin_k.setToolTip(Config.TOOLTIPS['k_value'])
        layout.addWidget(self.spin_k, 1, 5)
        
        # 트레일링 스톱 발동
        layout.addWidget(QLabel("🎯 TS 발동 수익률:"), 2, 0)
        self.spin_ts_start = QDoubleSpinBox()
        self.spin_ts_start.setRange(0.5, 30.0)
        self.spin_ts_start.setValue(Config.DEFAULT_TS_START)
        self.spin_ts_start.setSuffix(" %")
        self.spin_ts_start.setToolTip(Config.TOOLTIPS['ts_start'])
        layout.addWidget(self.spin_ts_start, 2, 1)
        
        # 트레일링 스톱 하락폭
        layout.addWidget(QLabel("📉 TS 하락폭:"), 2, 2)
        self.spin_ts_stop = QDoubleSpinBox()
        self.spin_ts_stop.setRange(0.5, 15.0)
        self.spin_ts_stop.setValue(Config.DEFAULT_TS_STOP)
        self.spin_ts_stop.setSuffix(" %")
        self.spin_ts_stop.setToolTip(Config.TOOLTIPS['ts_stop'])
        layout.addWidget(self.spin_ts_stop, 2, 3)
        
        # 손절률
        layout.addWidget(QLabel("🛑 절대 손절률:"), 2, 4)
        self.spin_loss = QDoubleSpinBox()
        self.spin_loss.setRange(0.5, 20.0)
        self.spin_loss.setValue(Config.DEFAULT_LOSS_CUT)
        self.spin_loss.setSuffix(" %")
        self.spin_loss.setToolTip(Config.TOOLTIPS['loss_cut'])
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
        
        # MACD 필터
        group_macd = QGroupBox("📉 MACD 필터")
        macd_layout = QGridLayout()
        
        self.chk_use_macd = QCheckBox("MACD 필터 사용 (골든크로스 확인)")
        self.chk_use_macd.setChecked(Config.DEFAULT_USE_MACD)
        self.chk_use_macd.setToolTip("MACD가 Signal선 위에 있을 때만 매수합니다.\n상승 모멘텀을 확인하여 진입 정확도를 높입니다.")
        macd_layout.addWidget(self.chk_use_macd, 0, 0, 1, 2)
        
        group_macd.setLayout(macd_layout)
        layout.addWidget(group_macd)
        
        # 거래량 필터
        group_vol = QGroupBox("📊 거래량 필터")
        vol_layout = QGridLayout()
        
        self.chk_use_volume = QCheckBox("거래량 필터 사용")
        self.chk_use_volume.setChecked(Config.DEFAULT_USE_VOLUME)
        self.chk_use_volume.setToolTip("평균 거래량 대비 현재 거래량이 충분할 때만 매수합니다.\n거래량이 수반되지 않은 가격 상승은 신뢰도가 낮습니다.")
        vol_layout.addWidget(self.chk_use_volume, 0, 0, 1, 2)
        
        vol_layout.addWidget(QLabel("거래량 배수:"), 1, 0)
        self.spin_volume_mult = QDoubleSpinBox()
        self.spin_volume_mult.setRange(1.0, 5.0)
        self.spin_volume_mult.setSingleStep(0.1)
        self.spin_volume_mult.setValue(Config.DEFAULT_VOLUME_MULTIPLIER)
        self.spin_volume_mult.setToolTip("현재 거래량 >= 평균 거래량 × 배수 일 때 진입\n예: 1.5 = 평균의 1.5배 이상")
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
        preset_layout = QVBoxLayout()
        
        # 프리셋 버튼 행
        btn_row = QHBoxLayout()
        
        btn_aggressive = QPushButton("🔥 공격적")
        btn_aggressive.setToolTip(Config.DEFAULT_PRESETS['aggressive']['description'])
        btn_aggressive.clicked.connect(lambda: self.apply_preset("aggressive"))
        
        btn_normal = QPushButton("⚖️ 표준")
        btn_normal.setToolTip(Config.DEFAULT_PRESETS['normal']['description'])
        btn_normal.clicked.connect(lambda: self.apply_preset("normal"))
        
        btn_conservative = QPushButton("🛡️ 보수적")
        btn_conservative.setToolTip(Config.DEFAULT_PRESETS['conservative']['description'])
        btn_conservative.clicked.connect(lambda: self.apply_preset("conservative"))
        
        btn_row.addWidget(btn_aggressive)
        btn_row.addWidget(btn_normal)
        btn_row.addWidget(btn_conservative)
        preset_layout.addLayout(btn_row)
        
        # 현재 프리셋 상태 및 관리 버튼
        manage_row = QHBoxLayout()
        
        self.lbl_current_preset = QLabel("💡 프리셋을 선택하거나 직접 값을 조정하세요")
        self.lbl_current_preset.setStyleSheet("color: #90e0ef; font-style: italic;")
        manage_row.addWidget(self.lbl_current_preset)
        
        manage_row.addStretch(1)
        
        btn_manage_presets = QPushButton("📁 프리셋 관리")
        btn_manage_presets.clicked.connect(self.open_preset_manager)
        manage_row.addWidget(btn_manage_presets)
        
        preset_layout.addLayout(manage_row)
        
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
        
        self.statusbar.addPermanentWidget(QLabel("Upbit Pro Algo-Trader v2.0"))

    def create_menu_bar(self):
        """메뉴바 생성"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu("파일")
        
        action_settings = QAction("⚙️ 시스템 설정", self)
        action_settings.triggered.connect(self.show_settings)
        file_menu.addAction(action_settings)
        
        file_menu.addSeparator()
        
        action_exit = QAction("❌ 종료", self)
        action_exit.triggered.connect(self.close)
        file_menu.addAction(action_exit)
        
        # 보기 메뉴
        view_menu = menubar.addMenu("보기")
        
        action_logs = QAction("📜 로그 폴더 열기", self)
        action_logs.triggered.connect(lambda: os.startfile(Config.LOG_DIR) if os.path.exists(Config.LOG_DIR) else None)
        view_menu.addAction(action_logs)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말")
        
        action_help = QAction("📚 사용 가이드", self)
        action_help.triggered.connect(self.show_help)
        help_menu.addAction(action_help)
        
        action_about = QAction("ℹ️ 정보", self)
        action_about.triggered.connect(lambda: QMessageBox.about(self, "정보", 
            "Upbit Pro Algo-Trader v2.0\n\n"
            "업비트 OpenAPI 기반 24시간 코인 자동매매 프로그램\n\n"
            "변동성 돌파 전략 + MA 필터 + 트레일링 스톱"))
        help_menu.addAction(action_about)

    def setup_tray(self):
        """시스템 트레이 설정"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # 트레이 아이콘 설정 (기본 아이콘 사용)
        self.tray_icon.setToolTip("Upbit Pro Trader")
        
        # 트레이 메뉴
        tray_menu = QMenu()
        
        action_show = QAction("표시", self)
        action_show.triggered.connect(self.show_from_tray)
        tray_menu.addAction(action_show)
        
        action_hide = QAction("숨기기", self)
        action_hide.triggered.connect(self.hide)
        tray_menu.addAction(action_hide)
        
        tray_menu.addSeparator()
        
        action_start = QAction("🚀 매매 시작", self)
        action_start.triggered.connect(self.start_trading)
        tray_menu.addAction(action_start)
        
        action_stop = QAction("⏹️ 매매 중지", self)
        action_stop.triggered.connect(self.stop_trading)
        tray_menu.addAction(action_stop)
        
        tray_menu.addSeparator()
        
        action_quit = QAction("종료", self)
        action_quit.triggered.connect(self.force_quit)
        tray_menu.addAction(action_quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        """트레이 아이콘 클릭 처리"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_from_tray()

    def show_from_tray(self):
        """트레이에서 창 다시 표시"""
        self.show()
        self.activateWindow()
        self.raise_()

    def force_quit(self):
        """프로그램 완전 종료 (트레이로 최소화 안함)"""
        self.system_settings['minimize_to_tray'] = False
        self.close()

    def check_first_run(self):
        """처음 실행 시 가이드 표시"""
        if not os.path.exists(Config.SETTINGS_FILE):
            reply = QMessageBox.question(self, "환영합니다! 👋",
                "Upbit Pro Algo-Trader에 오신 것을 환영합니다!\n\n"
                "처음 사용이시라면 빠른 시작 가이드를 \n"
                "확인하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.show_help()

    def open_preset_manager(self):
        """프리셋 관리자 열기"""
        current_values = {
            'k': self.spin_k.value(),
            'ts_start': self.spin_ts_start.value(),
            'ts_stop': self.spin_ts_stop.value(),
            'loss': self.spin_loss.value(),
            'betting': self.spin_betting.value(),
            'rsi_upper': self.spin_rsi_upper.value(),
            'max_holdings': self.spin_max_holdings.value()
        }
        
        dialog = PresetManagerDialog(self, current_values)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            preset = dialog.get_selected_preset()
            if preset:
                self.apply_preset_values(preset)

    def apply_preset_values(self, preset):
        """프리셋 값 적용"""
        if 'k' in preset:
            self.spin_k.setValue(preset['k'])
        if 'ts_start' in preset:
            self.spin_ts_start.setValue(preset['ts_start'])
        if 'ts_stop' in preset:
            self.spin_ts_stop.setValue(preset['ts_stop'])
        if 'loss' in preset:
            self.spin_loss.setValue(preset['loss'])
        if 'betting' in preset:
            self.spin_betting.setValue(preset['betting'])
        if 'rsi_upper' in preset:
            self.spin_rsi_upper.setValue(preset['rsi_upper'])
        if 'max_holdings' in preset:
            self.spin_max_holdings.setValue(preset['max_holdings'])
        
        name = preset.get('name', '사용자 정의')
        self.lbl_current_preset.setText(f"✅ 현재 프리셋: {name}")
        self.log(f"📋 {name} 프리셋 적용됨")

    def show_help(self):
        """도움말 다이얼로그 표시"""
        dialog = HelpDialog(self)
        dialog.exec()

    def show_settings(self):
        """시스템 설정 다이얼로그 표시"""
        dialog = SettingsDialog(self, self.system_settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_settings = dialog.get_settings()
            
            # Windows 시작 프로그램 설정 변경 처리
            if new_settings['run_at_startup'] != self.system_settings.get('run_at_startup', False):
                self.set_startup_registry(new_settings['run_at_startup'])
            
            self.system_settings.update(new_settings)
            self.save_settings()
            self.log("⚙️ 시스템 설정이 저장되었습니다")

    def set_startup_registry(self, enable):
        """Windows 시작 프로그램 레지스트리 설정"""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "UpbitProTrader"
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            
            if enable:
                # 현재 실행 파일 경로
                exe_path = sys.executable
                if getattr(sys, 'frozen', False):
                    exe_path = sys.executable
                else:
                    exe_path = os.path.abspath(sys.argv[0])
                
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"')
                self.log("✅ Windows 시작 시 자동 실행이 설정되었습니다")
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                    self.log("❌ Windows 시작 시 자동 실행이 해제되었습니다")
                except FileNotFoundError:
                    pass
            
            winreg.CloseKey(key)
        except Exception as e:
            self.logger.error(f"레지스트리 설정 실패: {e}")

    def send_notification(self, title, message):
        """트레이 알림 표시"""
        if self.system_settings.get('show_tray_notifications', True):
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)

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
            "max_holdings": self.spin_max_holdings.value(),
            # 시스템 설정
            "system": self.system_settings
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
                
                # 시스템 설정 불러오기
                if "system" in s:
                    self.system_settings.update(s["system"])
                
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

    def calculate_macd(self, ticker):
        """MACD 계산 (MACD, Signal, Histogram 반환)"""
        try:
            interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=50)
            if df is None or len(df) < 30:
                return 0, 0, 0
            
            close = df['close']
            
            # EMA 계산
            ema_fast = close.ewm(span=Config.DEFAULT_MACD_FAST, adjust=False).mean()
            ema_slow = close.ewm(span=Config.DEFAULT_MACD_SLOW, adjust=False).mean()
            
            # MACD = 단기 EMA - 장기 EMA
            macd = ema_fast - ema_slow
            
            # Signal = MACD의 9일 EMA
            signal = macd.ewm(span=Config.DEFAULT_MACD_SIGNAL, adjust=False).mean()
            
            # Histogram = MACD - Signal
            histogram = macd - signal
            
            return macd.iloc[-1], signal.iloc[-1], histogram.iloc[-1]
        except Exception as e:
            self.logger.error(f"MACD 계산 실패 ({ticker}): {e}")
            return 0, 0, 0

    def calculate_bollinger_bands(self, ticker):
        """볼린저 밴드 계산 (상단, 중간, 하단 반환)"""
        try:
            interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
            period = Config.DEFAULT_BB_PERIOD
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=period + 5)
            if df is None or len(df) < period:
                return None, None, None
            
            close = df['close']
            
            # 중간선 (SMA)
            middle = close.rolling(window=period).mean().iloc[-1]
            
            # 표준편차
            std = close.rolling(window=period).std().iloc[-1]
            
            # 상단/하단 밴드
            upper = middle + (std * Config.DEFAULT_BB_STD)
            lower = middle - (std * Config.DEFAULT_BB_STD)
            
            return upper, middle, lower
        except Exception as e:
            self.logger.error(f"볼린저 밴드 계산 실패 ({ticker}): {e}")
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
            
            # True Range 계산
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # ATR = True Range의 이동평균
            atr = tr.rolling(window=period).mean().iloc[-1]
            return atr
        except Exception as e:
            self.logger.error(f"ATR 계산 실패 ({ticker}): {e}")
            return None

    def calculate_volume_avg(self, ticker, period=20):
        """평균 거래량 계산"""
        try:
            interval = Config.CANDLE_INTERVALS[self.combo_candle.currentText()]
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=period + 1)
            if df is None or len(df) < period:
                return None, None
            
            current_volume = df.iloc[-1]['volume']
            avg_volume = df['volume'].iloc[:-1].mean()
            
            return current_volume, avg_volume
        except Exception as e:
            return None, None
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
        
        # 4. MACD 필터 (골든크로스: MACD > Signal)
        if hasattr(self, 'chk_use_macd') and self.chk_use_macd.isChecked():
            macd, signal, histogram = self.calculate_macd(ticker)
            if macd <= signal:
                self.log(f"[{ticker}] MACD {macd:.2f} <= Signal {signal:.2f} (하락세) 진입 보류")
                return
        
        # 5. 거래량 필터
        if self.chk_use_volume.isChecked():
            curr_vol, avg_vol = self.calculate_volume_avg(ticker, Config.DEFAULT_VOLUME_PERIOD)
            if curr_vol and avg_vol:
                required_vol = avg_vol * self.spin_volume_mult.value()
                if curr_vol < required_vol:
                    self.log(f"[{ticker}] 거래량 부족 ({curr_vol:,.0f} < {required_vol:,.0f}) 진입 보류")
                    return
        
        # 6. 리스크 관리
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
        if preset_type in Config.DEFAULT_PRESETS:
            preset = Config.DEFAULT_PRESETS[preset_type]
            self.apply_preset_values(preset)

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
        # 트레이로 최소화 옵션 확인
        if self.system_settings.get('minimize_to_tray', True) and self.isVisible():
            event.ignore()
            self.hide()
            self.send_notification("Upbit Pro Trader", "트레이로 최소화되었습니다. 더블클릭으로 다시 열 수 있습니다.")
            return
        
        if self.is_running:
            reply = QMessageBox.question(self, "종료 확인",
                "매매가 진행 중입니다. 정말 종료하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        
        self.price_thread.stop()
        self.price_thread.wait()
        self.tray_icon.hide()
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
