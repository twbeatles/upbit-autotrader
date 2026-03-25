from PyQt6.QtWidgets import (
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
)


def build_ops_tab(self):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(10)
    layout.setContentsMargins(15, 15, 15, 15)

    top_row = QHBoxLayout()
    self.lbl_manual_review_count = QLabel("🧾 수동검토 큐 0건")
    top_row.addWidget(self.lbl_manual_review_count)
    top_row.addStretch(1)

    self.btn_manual_review_refresh = QPushButton("🔄 새로고침")
    self.btn_manual_review_refresh.clicked.connect(self.refresh_manual_review_table)
    top_row.addWidget(self.btn_manual_review_refresh)

    self.btn_manual_review_requery = QPushButton("🔁 재조회")
    self.btn_manual_review_requery.clicked.connect(self.requery_selected_manual_review)
    top_row.addWidget(self.btn_manual_review_requery)

    self.btn_manual_review_resolve = QPushButton("✅ 해제")
    self.btn_manual_review_resolve.clicked.connect(self.resolve_selected_manual_review)
    top_row.addWidget(self.btn_manual_review_resolve)
    layout.addLayout(top_row)

    self.manual_review_table = QTableWidget()
    cols = ["queued_at", "age", "ticker", "uuid", "reason", "pending_state"]
    self.manual_review_table.setColumnCount(len(cols))
    self.manual_review_table.setHorizontalHeaderLabels(cols)
    header = self.manual_review_table.horizontalHeader()
    if header is not None:
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    self.manual_review_table.setAlternatingRowColors(True)
    self.manual_review_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    self.manual_review_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    vertical_header = self.manual_review_table.verticalHeader()
    if vertical_header is not None:
        vertical_header.setDefaultSectionSize(30)
    layout.addWidget(self.manual_review_table)

    if hasattr(self, "refresh_manual_review_table"):
        self.refresh_manual_review_table()
    return widget
