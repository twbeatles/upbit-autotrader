"""Main-window shell: dashboard + Fluent navigation rail + holdings/log splitter.

Fluent-style shell rules applied (DESKTOP_UI_DESIGN_RULES.md):
- spacing/margins come from design tokens (4/8/12/16/24/32 scale only)
- initial geometry follows the available screen area (responsive window)
- tabs use text + native style icons instead of emoji icons
- the holdings table owns an EmptyState overlay (initial/empty/error
  states are part of every page contract)
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QStyle,
    QStyledItemDelegate,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from upbit_autotrader.core.config import Config
from upbit_autotrader.ui import design_tokens as tokens
from upbit_autotrader.ui import navigation
from upbit_autotrader.ui.components.empty_state import EmptyState
from upbit_autotrader.ui.navigation import NavigationItemPosition
from upbit_autotrader.ui.theme import configure_fluent_window, configure_main_window

# Navigation pages: (factory method, text label, standard icon, rail position).
# Factories stay late-bound so pages keep building through the controller.
# Mirrors the reference MSFluentWindow layout: trading pages up top, the
# auxiliary operations page pinned to the bottom.
# Pages: (factory, label, fallback QStyle icon, reference Fluent icon, rail position).
NAV_LABELS = ("트레이딩", "전략 설정", "고급 설정", "거래 통계", "거래 내역", "입출금", "운영/수동검토")
TAB_DEFS = (
    ("create_trading_view", "트레이딩", "SP_ComputerIcon", "HOME", NavigationItemPosition.TOP),
    ("create_strategy_tab", "전략 설정", "SP_FileDialogDetailedView", "ROBOT", NavigationItemPosition.TOP),
    ("create_advanced_tab", "고급 설정", "SP_FileDialogContentsView", "SETTING", NavigationItemPosition.TOP),
    ("create_statistics_tab", "거래 통계", "SP_FileDialogInfoView", "PIE_SINGLE", NavigationItemPosition.TOP),
    ("create_history_tab", "거래 내역", "SP_FileDialogListView", "HISTORY", NavigationItemPosition.TOP),
    ("create_transfer_tab", "입출금", "SP_DialogSaveButton", "SAVE", NavigationItemPosition.TOP),
    ("create_ops_tab", "운영/수동검토", "SP_ToolBarHorizontalExtensionButton", "COMMAND_PROMPT", NavigationItemPosition.BOTTOM),
)


def _fluent_window_base():
    """Reference window class (None when unusable: missing or wrong binding)."""
    from upbit_autotrader.ui.qt_compat import fluent_window_base

    return fluent_window_base()


def _is_fluent_window(host) -> bool:
    base = _fluent_window_base()
    return base is not None and isinstance(host, base)

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
    """Assemble the main window (reference MSFluentWindow flow when available).

    With the Fluent dependency the window itself is the navigation shell and
    pages register through ``addSubInterface`` exactly like the reference
    main window; without it we fall back to the native rail container.
    """
    self.setWindowTitle("Upbit Pro Algo-Trader v2.7 [24H 코인 자동매매]")
    configure_main_window(self)
    configure_fluent_window(self)

    if _is_fluent_window(self):
        _register_pages(self, fluent=True)
        try:
            self.navigationInterface.setExpandWidth(200)
            self.navigationInterface.expand()
        except Exception:
            pass
    else:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        body = QHBoxLayout(central_widget)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        rail = navigation.FluentNavRail(central_widget)
        stack = QStackedWidget(central_widget)
        # Same surface as the Fluent shell: pages live on stackedWidget.
        self.stackedWidget = stack
        self.switchTo = _fallback_switch_to.__get__(self)
        stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.nav_shell = navigation.NavigationShell(rail, stack)
        _register_pages(self, fluent=False)
        body.addWidget(rail, 0)

        right = QWidget(central_widget)
        right_layout = QVBoxLayout(right)
        right_layout.setSpacing(tokens.SECTION_GAP)
        right_layout.setContentsMargins(
            tokens.PAGE_MARGIN, tokens.SPACE_MD, tokens.PAGE_MARGIN, tokens.PAGE_MARGIN
        )
        dashboard = self.create_dashboard()
        dashboard.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        right_layout.addWidget(dashboard, 0)
        right_layout.addWidget(stack, 1)
        body.addWidget(right, 1)

    self.create_statusbar()
    self.refresh_trade_action_buttons()
    self.refresh_table_empty_state()


def _build_trading_page(self, view: QWidget) -> QWidget:
    """Trading page: dashboard + scrollable view + monitoring splitter.

    The view keeps its natural height inside a scroll area and the
    holdings/log splitter owns a fixed minimum below it, so dense ticket
    controls can never be crushed into each other on short windows.
    """
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(tokens.SECTION_GAP)

    dashboard = self.create_dashboard()
    dashboard.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    layout.addWidget(dashboard, 0)

    splitter = QSplitter(Qt.Orientation.Vertical)
    splitter.setChildrenCollapsible(False)

    view_scroll = navigation.wrap_scrollable(view)
    view_scroll.setMinimumHeight(360)
    splitter.addWidget(view_scroll)

    monitor = self.create_splitter()
    monitor.setMinimumHeight(280)
    splitter.addWidget(monitor)
    splitter.setStretchFactor(0, 3)
    splitter.setStretchFactor(1, 2)
    splitter.setSizes([560, 340])
    layout.addWidget(splitter, 1)
    return page


def _register_pages(self, shell=None, fluent: bool = False) -> None:
    """Register every legacy page (legacy order kept).

    ``fluent=True`` registers on the MSFluentWindow itself through
    ``addSubInterface`` (reference call shape); otherwise on the native
    fallback shell stored at ``self.nav_shell``.
    """
    try:
        from qfluentwidgets import FluentIcon as FIF
        from qfluentwidgets import NavigationItemPosition as FluentPosition
    except ImportError:
        FIF = None  # type: ignore[assignment]
        FluentPosition = None  # type: ignore[assignment]

    already: set[str] = set()
    if fluent:
        try:
            already = {
                self.stackedWidget.widget(i).objectName()
                for i in range(self.stackedWidget.count())
            }
        except Exception:
            already = set()
    for factory_name, label, icon_name, fif_name, position in TAB_DEFS:
        if factory_name in already:
            continue
        factory = getattr(self, factory_name, None)
        if not callable(factory):
            continue
        page = factory()
        if not isinstance(page, QWidget):
            continue
        if factory_name == "create_trading_view":
            page = _build_trading_page(self, page)
        else:
            page = navigation.wrap_scrollable(page)
        page.setObjectName(factory_name)
        if fluent and FIF is not None and FluentPosition is not None:
            fluent_pos = (
                FluentPosition.BOTTOM
                if position == NavigationItemPosition.BOTTOM
                else FluentPosition.TOP
            )
            # NOTE: the 4th positional arg is the selected icon in the
            # reference API, so position must stay a keyword argument.
            self.addSubInterface(page, getattr(FIF, fif_name), label, position=fluent_pos)
        else:
            target = shell if shell is not None else getattr(self, "nav_shell", None)
            if target is None:
                continue
            icon = _tab_icon(target.stack, icon_name)
            target.addSubInterface(page, icon, label, position, key=factory_name)


def _fallback_switch_to(self, widget) -> None:
    """Native-shell counterpart of ``FluentWindow.switchTo(widget)``."""
    stack = getattr(self, "stackedWidget", None)
    if stack is None:
        return
    try:
        stack.setCurrentWidget(widget)
    except Exception:
        pass


def create_navigation(self):
    """Build a standalone native nav-shell container (tests/diagnostics entry).

    Returns the ``(rail | page stack)`` widget and stores the controller
    on ``self.nav_shell``; the live window uses ``init_ui`` instead.
    """
    container, shell = navigation.create_shell()
    self.nav_shell = shell
    _register_pages(self, shell=shell, fluent=False)
    return container


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
