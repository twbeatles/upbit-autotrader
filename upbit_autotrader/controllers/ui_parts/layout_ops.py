from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QScrollArea, QSizePolicy, QSplitter, QTabWidget, QTextEdit, QVBoxLayout, QWidget, QTableWidget, QHeaderView

from upbit_autotrader.core.config import Config


def init_ui(self):
    self.setWindowTitle("Upbit Pro Algo-Trader v2.7 [24H 코인 자동매매]")
    self.setGeometry(100, 100, 1200, 900)
    self.setMinimumSize(1000, 700)
    if hasattr(self, "setStyleSheet"):
        self.setStyleSheet(getattr(self, "_dark_stylesheet", ""))

    central_widget = QWidget()
    self.setCentralWidget(central_widget)

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    scroll_content = QWidget()
    content_layout = QVBoxLayout(scroll_content)
    content_layout.setSpacing(15)
    content_layout.setContentsMargins(15, 15, 15, 15)

    dashboard = self.create_dashboard()
    dashboard.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    content_layout.addWidget(dashboard, 0)

    tab_widget = self.create_tab_widget()
    tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    content_layout.addWidget(tab_widget, 0)
    content_layout.addWidget(self.create_splitter(), 1)

    scroll_area.setWidget(scroll_content)

    main_layout = QVBoxLayout(central_widget)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.addWidget(scroll_area)

    self.create_statusbar()
    self.refresh_trade_action_buttons()


def create_tab_widget(self):
    tab_widget = QTabWidget()
    tab_widget.addTab(self.create_strategy_tab(), "⚙️ 전략 설정")
    tab_widget.addTab(self.create_advanced_tab(), "🔬 고급 설정")
    tab_widget.addTab(self.create_statistics_tab(), "📊 거래 통계")
    tab_widget.addTab(self.create_history_tab(), "📝 거래 내역")
    tab_widget.addTab(self.create_ops_tab(), "🛠️ 운영/수동검토")
    return tab_widget


def create_splitter(self):
    splitter = QSplitter(Qt.Orientation.Vertical)
    splitter.setChildrenCollapsible(False)

    self.table = QTableWidget()
    cols = ["코인명", "현재가", "목표가", "MA(5)", "상태", "보유수량", "매입가", "수익률", "최고수익률", "투자금"]
    self.table.setColumnCount(len(cols))
    self.table.setHorizontalHeaderLabels(cols)
    header = self.table.horizontalHeader()
    if header is not None:
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    self.table.setAlternatingRowColors(True)
    self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    self.table.setMinimumHeight(200)
    vertical_header = self.table.verticalHeader()
    if vertical_header is not None:
        vertical_header.setDefaultSectionSize(35)

    self.log_text = QTextEdit()
    self.log_text.setMinimumHeight(150)
    self.log_text.setReadOnly(True)
    self.log_text.setPlaceholderText("로그가 여기에 표시됩니다...")
    document = self.log_text.document()
    if document is not None:
        document.setMaximumBlockCount(Config.MAX_LOG_LINES)

    splitter.addWidget(self.table)
    splitter.addWidget(self.log_text)
    splitter.setStretchFactor(0, 3)
    splitter.setStretchFactor(1, 1)
    splitter.setSizes([400, 200])
    return splitter
