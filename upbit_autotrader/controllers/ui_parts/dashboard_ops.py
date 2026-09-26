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
from upbit_autotrader.ui.theme import is_dark_mode


def _stat_card_style() -> str:
    c = tokens.palette(is_dark_mode())
    return (
        "QLabel {"
        f" background-color: {c['surface']};"
        f" border: 1px solid {c['border']};"
        f" border-radius: {tokens.CARD_RADIUS}px;"
        f" padding: {tokens.SPACE_MD}px;"
        f" font-size: {tokens.FONT_BODY}px;"
        "}"
    )


def create_dashboard(self):
    group_dash = QGroupBox("Trading Dashboard")
    layout_dash = QHBoxLayout()
    layout_dash.setSpacing(tokens.SPACE_MD)

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

    self.btn_login = QPushButton("시스템 접속")
    self.btn_login.setObjectName("loginBtn")
    self.btn_login.setProperty("primary", True)
    try:
        self.btn_login.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        )
    except Exception:
        pass
    self.btn_login.setMinimumSize(120, tokens.CONTROL_HEIGHT_MD)
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

    stat_style = _stat_card_style()

    self.stat_trades = QLabel("총 거래 횟수\n0 회")
    self.stat_trades.setStyleSheet(stat_style)
    self.stat_trades.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(self.stat_trades, 0, 0)

    self.stat_winrate = QLabel("승률\n0.0 %")
    self.stat_winrate.setStyleSheet(stat_style)
    self.stat_winrate.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(self.stat_winrate, 0, 1)

    self.stat_profit = QLabel("총 실현손익\n0 원")
    self.stat_profit.setStyleSheet(stat_style)
    self.stat_profit.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(self.stat_profit, 0, 2)

    self.stat_holdings = QLabel("보유 종목\n0 개")
    self.stat_holdings.setStyleSheet(stat_style)
    self.stat_holdings.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(self.stat_holdings, 0, 3)

    btn_reset = QPushButton("통계 초기화")
    btn_reset.clicked.connect(self.reset_statistics)
    layout.addWidget(btn_reset, 1, 0, 1, 4)
    layout.setRowStretch(2, 1)
    return widget


def create_statusbar(self):
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
