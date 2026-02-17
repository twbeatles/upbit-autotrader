import datetime
import json
import os
import re

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
)

from upbit_config import Config

try:
    from upbit_dialogs import DARK_STYLESHEET
except ImportError:
    DARK_STYLESHEET = ""

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

