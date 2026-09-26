"""Main-window shell: dashboard + navigation tabs + holdings/log splitter.

Fluent-style shell rules applied (DESKTOP_UI_DESIGN_RULES.md):
- spacing/margins come from design tokens (4/8/12/16/24/32 scale only)
- initial geometry follows the available screen area (responsive window)
- tabs use text + native style icons instead of emoji icons
- the holdings table owns an EmptyState overlay (initial/empty/error
  states are part of every page contract)
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHeaderView,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStyle,
    QStyledItemDelegate,
    QTabWidget,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from upbit_autotrader.core.config import Config
from upbit_autotrader.ui import design_tokens as tokens
from upbit_autotrader.ui.components.empty_state import EmptyState
from upbit_autotrader.ui.theme import configure_main_window

# Navigation pages: (factory method, text label, standard icon).
# Factories stay late-bound so pages keep building through the controller.
TAB_DEFS = (
    ("create_trading_view", "트레이딩", "SP_ComputerIcon"),
    ("create_strategy_tab", "전략 설정", "SP_FileDialogDetailedView"),
    ("create_advanced_tab", "고급 설정", "SP_FileDialogContentsView"),
    ("create_statistics_tab", "거래 통계", "SP_FileDialogInfoView"),
    ("create_history_tab", "거래 내역", "SP_FileDialogListView"),
    ("create_transfer_tab", "입출금", "SP_DialogSaveButton"),
    ("create_ops_tab", "운영/수동검토", "SP_ToolBarHorizontalExtensionButton"),
)

TABLE_COLUMNS = [
    "코인명",
    "현재가",
    "목표가",
    "MA(5)",
    "상태",
    "보유수량",
    "매입가",
    "수익률",
    "최고수익률",
    "투자금",
    "매수",
    "매도",
]

# Numeric columns right-align, the status column centers (rules section 14).
NUMERIC_COLUMNS = frozenset({1, 2, 3, 5, 6, 7, 8, 9})
CENTERED_COLUMNS = frozenset({4})


class HoldingsAlignDelegate(QStyledItemDelegate):
    """Column alignment for the holdings table (no per-cell changes needed)."""

    def initStyleOption(self, option, index) -> None:
        super().initStyleOption(option, index)
        if option is None:
            return
        col = index.column() if index is not None else -1
        if col in NUMERIC_COLUMNS:
            option.displayAlignment = (
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        elif col in CENTERED_COLUMNS:
            option.displayAlignment = (
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            )


def _tab_icon(widget: QWidget, name: str):
    try:
        style = widget.style()
        if style is None:
            return None
        return style.standardIcon(getattr(QStyle.StandardPixmap, name))
    except Exception:
        return None


def init_ui(self):
    self.setWindowTitle("Upbit Pro Algo-Trader v2.7 [24H 코인 자동매매]")
    configure_main_window(self)

    central_widget = QWidget()
    self.setCentralWidget(central_widget)

    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    scroll_content = QWidget()
    content_layout = QVBoxLayout(scroll_content)
    content_layout.setSpacing(tokens.SECTION_GAP)
    content_layout.setContentsMargins(
        tokens.PAGE_MARGIN, tokens.SPACE_MD, tokens.PAGE_MARGIN, tokens.PAGE_MARGIN
    )

    dashboard = self.create_dashboard()
    dashboard.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    content_layout.addWidget(dashboard, 0)

    self.tab_widget = self.create_tab_widget()
    self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    content_layout.addWidget(self.tab_widget, 0)
    content_layout.addWidget(self.create_splitter(), 1)

    scroll_area.setWidget(scroll_content)

    main_layout = QVBoxLayout(central_widget)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.addWidget(scroll_area)

    self.create_statusbar()
    self.refresh_trade_action_buttons()
    self.refresh_table_empty_state()


def create_tab_widget(self):
    tab_widget = QTabWidget()
    tab_widget.setDocumentMode(True)
    for factory_name, label, icon_name in TAB_DEFS:
        factory = getattr(self, factory_name, None)
        if not callable(factory):
            continue
        page = factory()
        if not isinstance(page, QWidget):
            continue
        icon = _tab_icon(tab_widget, icon_name)
        if icon is not None:
            tab_widget.addTab(page, icon, label)
        else:
            tab_widget.addTab(page, label)
    return tab_widget


def create_splitter(self):
    splitter = QSplitter(Qt.Orientation.Vertical)
    splitter.setChildrenCollapsible(False)

    table_stack = QStackedWidget()
    self.table = QTableWidget()
    self.table.setColumnCount(len(TABLE_COLUMNS))
    self.table.setHorizontalHeaderLabels(TABLE_COLUMNS)
    header = self.table.horizontalHeader()
    if header is not None:
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
    self.table.setItemDelegate(HoldingsAlignDelegate(self.table))
    self.table.setAlternatingRowColors(True)
    self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    self.table.setMinimumHeight(200)
    vertical_header = self.table.verticalHeader()
    if vertical_header is not None:
        vertical_header.setDefaultSectionSize(35)
    table_stack.addWidget(self.table)

    self.table_empty_state = EmptyState(
        "표시할 종목이 없습니다",
        "전략을 시작하면 감시 종목과 보유 현황이 여기에 표시됩니다.",
    )
    table_stack.addWidget(self.table_empty_state)
    table_stack.setCurrentWidget(self.table)
    self.table_stack = table_stack

    self.log_text = QTextEdit()
    self.log_text.setMinimumHeight(150)
    self.log_text.setReadOnly(True)
    self.log_text.setPlaceholderText("로그가 여기에 표시됩니다...")
    document = self.log_text.document()
    if document is not None:
        document.setMaximumBlockCount(Config.MAX_LOG_LINES)

    splitter.addWidget(table_stack)
    splitter.addWidget(self.log_text)
    splitter.setStretchFactor(0, 3)
    splitter.setStretchFactor(1, 1)
    splitter.setSizes([400, 200])
    return splitter


def refresh_table_empty_state(self) -> None:
    """Toggle the holdings-table EmptyState overlay (safe to call anytime)."""
    stack = getattr(self, "table_stack", None)
    table = getattr(self, "table", None)
    empty = getattr(self, "table_empty_state", None)
    if stack is None or table is None or empty is None:
        return
    try:
        has_rows = table.rowCount() > 0
    except Exception:
        has_rows = True
    try:
        stack.setCurrentWidget(table if has_rows else empty)
    except Exception:
        pass


def table_state_label(self) -> QLabel | None:
    """Accessor for the empty-state title (tests/diagnostics)."""
    empty = getattr(self, "table_empty_state", None)
    if empty is None:
        return None
    return empty.title_label
