"""Foundation tests for the Fluent-style UI redesign.

Covers design tokens, the central theme stylesheet, reusable components,
and the main-window shell (tabs keep every legacy page, inline QSS and
emoji icons are gone, the holdings table owns an empty state).
"""
import os

from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget

from upbit_autotrader.controllers import ui_parts as _ui_parts
from upbit_autotrader.controllers.ui_parts import layout_ops
from upbit_autotrader.ui import design_tokens as tokens
from upbit_autotrader.ui.components import EmptyState, InfoBar, SectionHeader, notify
from upbit_autotrader.ui.components.status_badge import StatusBadge
from upbit_autotrader.ui.theme import (
    build_stylesheet,
    is_dark_mode,
    preferred_window_size,
)

_APP = None


def _app():
    global _APP
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication(["pytest-fluent-ui"])
    _APP = app
    return app


def test_spacing_scale_uses_only_allowed_values():
    assert {
        tokens.SPACE_XXS,
        tokens.SPACE_XS,
        tokens.SPACE_SM,
        tokens.SPACE_MD,
        tokens.SPACE_LG,
        tokens.SPACE_XL,
    } == {4, 8, 12, 16, 24, 32}
    assert tokens.PAGE_MARGIN == 24
    assert tokens.SECTION_GAP == 24


def test_palette_has_semantic_keys_for_both_modes():
    for dark in (True, False):
        colors = tokens.palette(dark)
        for key in (
            "primary",
            "background",
            "surface",
            "surface_alt",
            "border",
            "text_primary",
            "text_secondary",
            "success",
            "warning",
            "error",
        ):
            assert colors[key].startswith("#"), (dark, key)
    assert tokens.palette(True)["background"] != tokens.palette(False)["background"]


def test_stylesheet_covers_both_themes_and_trade_actions():
    for dark in (True, False):
        sheet = build_stylesheet(dark)
        assert "QPushButton" in sheet
        assert 'primary="true"' in sheet
        assert 'destructive="true"' in sheet
        assert 'tradeBuy="true"' in sheet
        assert 'tradeSell="true"' in sheet
        assert "?" * 2 not in sheet
        sheet.encode("utf-8")


def test_preferred_window_size_clamps_to_screen():
    assert preferred_window_size(5000, 3000) == (1200, 900)
    width, height = preferred_window_size(1400, 900)
    assert (width, height) == (1200, 860)
    # tiny screens fall back to the minimum window floor (srtgo pattern)
    assert preferred_window_size(500, 400) == (960, 680)


def test_components_construct_headless():
    _app()
    header = SectionHeader("제목", "설명")
    assert header.title_label.text() == "제목"
    assert not header.subtitle_label.isHidden()
    plain = SectionHeader("제목만")
    assert plain.subtitle_label.isHidden()

    empty = EmptyState("비어 있음", "힌트")
    assert empty.title_label.text() == "비어 있음"

    badge = StatusBadge("연결 대기", "warning")
    assert badge.kind() == "warning"
    badge.set_kind("success")
    assert badge.kind() == "success"


def test_infobar_shows_and_caps_banners():
    _app()
    host = QMainWindow()
    central = host.centralWidget()
    assert central is None
    from PyQt6.QtWidgets import QVBoxLayout, QWidget

    central = QWidget()
    central.setLayout(QVBoxLayout())
    host.setCentralWidget(central)
    bars = [notify(host, f"제목{i}", kind="info", duration_ms=0) for i in range(5)]
    assert all(isinstance(bar, InfoBar) for bar in bars)
    host_widget = host.findChild(QWidget, "infoBarHost")
    assert host_widget is not None
    host_layout = host_widget.layout()
    assert host_layout is not None
    visible = []
    for i in range(host_layout.count()):
        item = host_layout.itemAt(i)
        child = item.widget() if item is not None else None
        if isinstance(child, InfoBar):
            visible.append(child)
    assert len(visible) <= 3


def _page_host():
    _app()
    from types import SimpleNamespace

    from upbit_autotrader.controllers import ui_parts as parts
    from upbit_autotrader.controllers.history_controller import TraderHistoryController
    from upbit_autotrader.controllers.ui_sections import (
        build_advanced_tab,
        build_ops_tab,
    )

    def _noop(*_args, **_kwargs):
        return None

    host = SimpleNamespace(
        strategy=object(),
        upbit=None,
        trade_history=[],
        login=_noop,
        reset_statistics=_noop,
        save_settings=_noop,
        start_trading=_noop,
        stop_trading=_noop,
        execute_batch_sell=_noop,
        execute_batch_buy=_noop,
        apply_preset=_noop,
        open_preset_manager=_noop,
        show_emergency_dialog=_noop,
        clear_today_history=_noop,
        export_history=_noop,
        refresh_transfer_history=_noop,
        refresh_manual_review_table=_noop,
        requery_selected_manual_review=_noop,
        resolve_selected_manual_review=_noop,
    )
    host.create_dashboard = lambda: parts.dashboard_ops.create_dashboard(host)
    host.create_trading_view = lambda: parts.trading_view_ops.build_trading_view(host)
    host.create_strategy_tab = lambda: parts.strategy_tab_ops.create_strategy_tab(host)
    host.create_advanced_tab = lambda: build_advanced_tab(host)
    host.create_statistics_tab = lambda: parts.dashboard_ops.create_statistics_tab(host)
    host._load_history_to_table = lambda: TraderHistoryController._load_history_to_table(host)  # type: ignore[arg-type]
    host.create_history_tab = lambda: TraderHistoryController.create_history_tab(host)  # type: ignore[arg-type]
    host.create_transfer_tab = lambda: TraderHistoryController.create_transfer_tab(host)  # type: ignore[arg-type]
    host.create_ops_tab = lambda: build_ops_tab(host)
    return host


def _is_emoji(ch: str) -> bool:
    code = ord(ch)
    return (
        0x1F000 <= code <= 0x1FAFF
        or 0x2600 <= code <= 0x27BF
        or 0x2B00 <= code <= 0x2BFF
        or 0xFE00 <= code <= 0xFE0F
        or code == 0x200D
        or 0x2190 <= code <= 0x21FF
    )


def test_tab_shell_keeps_all_legacy_pages_without_emoji():
    host = _page_host()
    widget = layout_ops.create_tab_widget(host)
    assert isinstance(widget, QTabWidget)
    labels = [widget.tabText(i) for i in range(widget.count())]
    assert labels == ["트레이딩", "전략 설정", "고급 설정", "거래 통계", "거래 내역", "입출금", "운영/수동검토"]
    for label in labels:
        assert not any(_is_emoji(ch) for ch in label), label


def test_splitter_table_owns_empty_state_overlay():
    host = _page_host()
    splitter = layout_ops.create_splitter(host)
    assert splitter.count() == 2
    assert host.table.rowCount() == 0
    host.refresh_table_empty_state = layout_ops.refresh_table_empty_state.__get__(host)
    host.refresh_table_empty_state()
    assert host.table_stack.currentWidget() is host.table_empty_state
    host.table.setRowCount(1)
    host.refresh_table_empty_state()
    assert host.table_stack.currentWidget() is host.table


def test_no_inline_hex_stylesheet_in_migrated_shell():
    import pathlib

    repo = pathlib.Path(__file__).resolve().parents[1]
    offenders = []
    for rel in (
        "upbit_autotrader/controllers/ui_parts/layout_ops.py",
        "upbit_autotrader/controllers/ui_parts/dashboard_ops.py",
        "upbit_autotrader/controllers/ui_parts/strategy_tab_ops.py",
        "upbit_autotrader/controllers/ui_parts/row_action_ops.py",
        "upbit_autotrader/controllers/ui_parts/order_ticket_ops.py",
    ):
        text = (repo / rel).read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            if "setStyleSheet" in line and "#" in line:
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert not offenders, "inline hex QSS remains:\n" + "\n".join(offenders)


def test_dark_mode_detection_returns_bool():
    assert isinstance(is_dark_mode(), bool)


def test_chart_colors_follow_theme():
    dark = tokens.chart_colors(True)
    light = tokens.chart_colors(False)
    assert set(dark) == {"background", "grid", "text"}
    assert dark["background"] != light["background"]


def test_holdings_delegate_column_sets():
    assert layout_ops.NUMERIC_COLUMNS == frozenset({1, 2, 3, 5, 6, 7, 8, 9})
    assert layout_ops.CENTERED_COLUMNS == frozenset({4})
    assert not (layout_ops.NUMERIC_COLUMNS & layout_ops.CENTERED_COLUMNS)


def test_notify_or_fallback_prefers_infobar_methods():
    from upbit_autotrader.ui.components.infobar import notify_or_fallback

    calls = []

    class _Host:
        def notify_success(self, title, message=""):
            calls.append((title, message))
            return "ok"

    assert notify_or_fallback(_Host(), "success", "T", "M") == "ok"
    assert calls == [("T", "M")]

    ran = []
    assert notify_or_fallback(object(), "info", "T", fallback=lambda: ran.append(1)) is None
    assert ran == [1]


def test_login_busy_helper_toggles_button():
    _app()
    from types import SimpleNamespace

    from PyQt6.QtWidgets import QPushButton

    from upbit_autotrader.controllers.trading_parts.order_api import auth as _auth

    btn = QPushButton("시스템 접속")
    host = SimpleNamespace(btn_login=btn)
    _auth._set_login_busy(host, True)
    assert not btn.isEnabled()
    assert btn.text() == "접속 중..."
    _auth._set_login_busy(host, False)
    assert btn.isEnabled()
    assert btn.text() == "시스템 접속"
    _auth._set_login_busy(SimpleNamespace(), True)


def test_ui_parts_package_still_exposes_builders():
    for name in (
        "dashboard_ops",
        "layout_ops",
        "order_ticket_ops",
        "trading_view_ops",
        "strategy_tab_ops",
    ):
        assert hasattr(_ui_parts, name), name
