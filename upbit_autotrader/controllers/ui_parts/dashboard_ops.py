from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget


def create_dashboard(self):
    group_dash = QGroupBox("📊 Trading Dashboard")
    layout_dash = QHBoxLayout()
    layout_dash.setSpacing(15)

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

    self.btn_login = QPushButton("🔌 시스템 접속")
    self.btn_login.setObjectName("loginBtn")
    self.btn_login.setMinimumSize(120, 40)
    self.btn_login.clicked.connect(self.login)
    layout_dash.addWidget(self.btn_login)

    layout_dash.addSpacing(20)
    self.lbl_balance = QLabel("💰 주문가능금액: 0 원")
    self.lbl_balance.setObjectName("depositLabel")
    layout_dash.addWidget(self.lbl_balance)

    self.lbl_total_profit = QLabel("📈 당일 실현손익: 0 원")
    self.lbl_total_profit.setObjectName("profitLabel")
    layout_dash.addWidget(self.lbl_total_profit)
    layout_dash.addStretch(1)

    self.lbl_connection = QLabel("● 연결 대기")
    self.lbl_connection.setStyleSheet("color: #ffc107; font-weight: bold;")
    layout_dash.addWidget(self.lbl_connection)

    group_dash.setLayout(layout_dash)
    return group_dash


def create_statistics_tab(self):
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


def create_statusbar(self):
    self.statusbar = self.statusBar()
    if self.statusbar is None:
        return

    self.status_time = QLabel()
    self.statusbar.addWidget(self.status_time)
    self.statusbar.addWidget(QLabel(" | "))

    self.status_trading = QLabel("● 대기 중")
    self.status_trading.setStyleSheet("color: #ffc107;")
    self.statusbar.addWidget(self.status_trading)

    self.statusbar.addWidget(QLabel(" | "))
    self.status_realtime = QLabel("실시간: 비활성")
    self.statusbar.addWidget(self.status_realtime)
    self.statusbar.addWidget(QLabel(" | "))
    self.status_market_regime = QLabel("MR: neutral 50.0")
    self.statusbar.addWidget(self.status_market_regime)

    self.statusbar.addPermanentWidget(QLabel("Upbit Pro Algo-Trader v2.7"))
