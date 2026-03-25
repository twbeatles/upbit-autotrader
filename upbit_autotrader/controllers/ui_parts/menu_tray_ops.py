import os
from typing import Any, cast


Config = cast(Any, None)
QAction = cast(Any, None)
QMenu = cast(Any, None)
QMessageBox = cast(Any, None)
QSystemTrayIcon = cast(Any, None)
ANALYTICS_AVAILABLE = False
BACKTESTER_AVAILABLE = False


def bind_runtime(**kwargs):
    globals().update(kwargs)


def create_menu_bar(self):
    menubar = self.menuBar()
    if menubar is None:
        return

    file_menu = menubar.addMenu("파일")
    if file_menu is None:
        return
    action_settings = QAction("⚙️ 시스템 설정", self)
    action_settings.triggered.connect(self.show_settings)
    file_menu.addAction(action_settings)
    file_menu.addSeparator()
    action_exit = QAction("❌ 종료", self)
    action_exit.triggered.connect(self.close)
    file_menu.addAction(action_exit)

    view_menu = menubar.addMenu("보기")
    if view_menu is None:
        return
    action_logs = QAction("📜 로그 폴더 열기", self)
    action_logs.triggered.connect(lambda: os.startfile(Config.LOG_DIR) if os.path.exists(Config.LOG_DIR) else None)
    view_menu.addAction(action_logs)

    tools_menu = menubar.addMenu("도구")
    if tools_menu is None:
        return
    action_analytics = QAction("📊 거래 분석 리포트", self)
    action_analytics.triggered.connect(self.generate_analytics_report)
    action_analytics.setEnabled(ANALYTICS_AVAILABLE)
    tools_menu.addAction(action_analytics)

    action_backtest = QAction("🧪 백테스트 실행", self)
    action_backtest.triggered.connect(self.run_backtest)
    action_backtest.setEnabled(BACKTESTER_AVAILABLE)
    tools_menu.addAction(action_backtest)
    tools_menu.addSeparator()

    action_export_history = QAction("💾 거래 내역 내보내기", self)
    action_export_history.triggered.connect(self.export_trade_history)
    tools_menu.addAction(action_export_history)

    help_menu = menubar.addMenu("도움말")
    if help_menu is None:
        return
    action_help = QAction("📚 사용 가이드", self)
    action_help.triggered.connect(self.show_help)
    help_menu.addAction(action_help)

    action_about = QAction("ℹ️ 정보", self)
    action_about.triggered.connect(
        lambda: QMessageBox.about(
            self,
            "정보",
            "Upbit Pro Algo-Trader v2.7\n\n"
            "업비트 OpenAPI 기반 24시간 코인 자동매매 프로그램\n\n"
            "변동성 돌파 전략 + MA 필터 + 트레일링 스톱",
        )
    )
    help_menu.addAction(action_about)


def setup_tray(self):
    self.tray_icon = QSystemTrayIcon(parent=self)
    style = self.style()
    if style is None:
        return
    self.tray_icon.setIcon(style.standardIcon(style.StandardPixmap.SP_ComputerIcon))
    self.tray_icon.setToolTip("Upbit Pro Trader v2.7")

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
    if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
        self.show_from_tray()


def show_from_tray(self):
    self.show()
    self.activateWindow()
    self.raise_()


def force_quit(self):
    self.system_settings["minimize_to_tray"] = False
    self.close()
