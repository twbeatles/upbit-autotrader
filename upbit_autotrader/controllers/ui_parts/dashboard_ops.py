"""Top dashboard: credentials, equity summary, connection status + statistics tab."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyle,
    QWidget,
)

from upbit_autotrader.ui import design_tokens as tokens
from upbit_autotrader.ui.components.status_badge import set_status_badge


def create_dashboard(self):
    group_dash = QGroupBox("Trading Dashboard")
    layout_dash = QHBoxLayout()
    layout_dash.setSpacing(tokens.SPACE_MD)

    layout_dash.addWidget(QLabel("Access:"))
    self.input_access = QLineEdit()
    self.input_access.setEchoMode(QLineEdit.EchoMode.Password)
    self.input_access.setMinimumWidth(120)
    self.input_access.setPlaceholderText("Access Key")
    layout_dash.addWidget(self.input_access)

    layout_dash.addWidget(QLabel("Secret:"))
    self.input_secret = QLineEdit()
    self.input_secret.setEchoMode(QLineEdit.EchoMode.Password)
    self.input_secret.setMinimumWidth(120)
    self.input_secret.setPlaceholderText("Secret Key")
    layout_dash.addWidget(self.input_secret)

    self.btn_login = QPushButton("시스템 접속")
    self.btn_login.setObjectName("loginBtn")
    self.btn_login.setProperty("primary", True)
    try:
        self.btn_login.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        )
    except Exception:
        pass
    self.btn_login.setMinimumSize(100, tokens.CONTROL_HEIGHT_MD)
    self.btn_login.clicked.connect(self.login)
    layout_dash.addWidget(self.btn_login)

    layout_dash.addSpacing(tokens.SPACE_LG)
    self.lbl_balance = QLabel("주문가능금액: 0 원")
    self.lbl_balance.setObjectName("depositLabel")
    layout_dash.addWidget(self.lbl_balance)

    self.lbl_total_profit = QLabel("당일 실현손익: 0 원")
    self.lbl_total_profit.setObjectName("profitLabel")
    layout_dash.addWidget(self.lbl_total_profit)
    layout_dash.addStretch(1)

    self.lbl_connection = QLabel("연결 대기")
    self.lbl_connection.setObjectName("connectionBadge")
    set_status_badge(self.lbl_connection, "warning")
    layout_dash.addWidget(self.lbl_connection)

    group_dash.setLayout(layout_dash)
    return group_dash


def create_statistics_tab(self):
    widget = QWidget()
    layout = QGridLayout(widget)
    layout.setSpacing(tokens.SPACE_LG)
    layout.setContentsMargins(
        tokens.PAGE_MARGIN, tokens.PAGE_MARGIN, tokens.PAGE_MARGIN, tokens.PAGE_MARGIN
    )

    self.stat_trades = QLabel("총 거래 횟수\n0 회")
    self.stat_trades.setProperty("statCard", True)
    self.stat_trades.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(self.stat_trades, 0, 0)

    self.stat_winrate = QLabel("승률\n0.0 %")
    self.stat_winrate.setProperty("statCard", True)
    self.stat_winrate.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(self.stat_winrate, 0, 1)

    self.stat_profit = QLabel("총 실현손익\n0 원")
    self.stat_profit.setProperty("statCard", True)
    self.stat_profit.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(self.stat_profit, 0, 2)

    self.stat_holdings = QLabel("보유 종목\n0 개")
    self.stat_holdings.setProperty("statCard", True)
    self.stat_holdings.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(self.stat_holdings, 0, 3)

    btn_reset = QPushButton("통계 초기화")
    btn_reset.clicked.connect(self.reset_statistics)
    layout.addWidget(btn_reset, 1, 0, 1, 4)
    layout.setRowStretch(2, 1)
    return widget


def create_statusbar(self):
    # init_ui may run more than once (bootstrap + explicit calls): never
    # build a second bar, which would squeeze the content sideways.
    if getattr(self, "statusbar", None) is not None and getattr(self, "status_time", None) is not None:
        return
    # MSFluentWindow is QWidget-based (no QMainWindow status bar): the same
    # live labels dock into a slim footer strip under the window content.
    if not hasattr(self, "statusBar"):
        strip = QWidget()
        strip.setObjectName("statusStrip")
        row = QHBoxLayout(strip)
        row.setContentsMargins(tokens.SPACE_MD, tokens.SPACE_XS, tokens.SPACE_MD, tokens.SPACE_XS)
        row.setSpacing(tokens.SPACE_XS)
        self.status_time = QLabel()
        row.addWidget(self.status_time)
        row.addWidget(QLabel(" | "))
        self.status_trading = QLabel("대기 중")
        set_status_badge(self.status_trading, "warning")
        row.addWidget(self.status_trading)
        row.addWidget(QLabel(" | "))
        self.status_realtime = QLabel("실시간: 비활성")
        row.addWidget(self.status_realtime)
        row.addWidget(QLabel(" | "))
        self.status_market_regime = QLabel("MR: neutral 50.0")
        row.addWidget(self.status_market_regime)
        row.addStretch(1)
        row.addWidget(QLabel("Upbit Pro Algo-Trader v2.7"))
        # Fluent windows nest the page stack inside an inner horizontal box
        # (rail | stack): wrap the stack and the strip in a vertical column
        # so the strip docks under the content instead of squeezing it.
        placed = False
        try:
            from PyQt6.QtWidgets import QVBoxLayout

            def _host_of(layout, widget):
                try:
                    if layout.indexOf(widget) >= 0:
                        return layout
                except Exception:
                    return None
                for i in range(layout.count()):
                    try:
                        sub = layout.itemAt(i).layout()
                    except Exception:
                        sub = None
                    if sub is not None:
                        found = _host_of(sub, widget)
                        if found is not None:
                            return found
                return None

            stack = getattr(self, "stackedWidget", None)
            root_layout = self.layout()
            host_layout = (
                _host_of(root_layout, stack)
                if stack is not None and root_layout is not None
                else None
            )
            if stack is not None and host_layout is not None:
                index = host_layout.indexOf(stack)
                host_layout.removeWidget(stack)
                column = QWidget()
                column_layout = QVBoxLayout(column)
                column_layout.setContentsMargins(0, 0, 0, 0)
                column_layout.setSpacing(0)
                column_layout.addWidget(stack, 1)
                column_layout.addWidget(strip, 0)
                try:
                    host_layout.insertWidget(index, column, 1)
                except TypeError:
                    host_layout.insertWidget(index, column)
                placed = True
        except Exception:
            placed = False
        if not placed:
            fallback = self.layout()
            if fallback is not None:
                fallback.addWidget(strip)
        self.statusbar = strip
        return

    self.statusbar = self.statusBar()
    if self.statusbar is None:
        return

    self.status_time = QLabel()
    self.statusbar.addWidget(self.status_time)
    self.statusbar.addWidget(QLabel(" | "))

    self.status_trading = QLabel("대기 중")
    set_status_badge(self.status_trading, "warning")
    self.statusbar.addWidget(self.status_trading)

    self.statusbar.addWidget(QLabel(" | "))
    self.status_realtime = QLabel("실시간: 비활성")
    self.statusbar.addWidget(self.status_realtime)
    self.statusbar.addWidget(QLabel(" | "))
    self.status_market_regime = QLabel("MR: neutral 50.0")
    self.statusbar.addWidget(self.status_market_regime)

    self.statusbar.addPermanentWidget(QLabel("Upbit Pro Algo-Trader v2.7"))
