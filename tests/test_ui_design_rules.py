"""Design-rule guards for the Fluent-style UI redesign.

Locks the DESKTOP_UI_DESIGN_RULES.md fixes in place:

- dialogs follow the OS theme (no pinned dark stylesheet, no per-dialog QSS)
- pages carry no inline ``setStyleSheet`` (stat cards use the ``statCard``
  dynamic property owned by the global theme)
- chart colors reuse design tokens (no duplicated hex)
- no emoji glyphs in widget-visible strings (labels, table cells,
  ops-alert/notification messages)
- non-destructive dialog feedback prefers InfoBar over modal QMessageBox
"""

import os
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]
UI_PARTS = REPO / "upbit_autotrader" / "controllers" / "ui_parts"
DIALOGS_DIR = REPO / "upbit_autotrader" / "ui" / "dialogs"
FALLBACKS = REPO / "upbit_autotrader" / "ui" / "dialog_fallbacks.py"

_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE00-\uFE0F\u2190-\u21FF\u200D]"
)
_UI_LINE_TRIGGERS = ("setText", "set_table_item", "_ops_alert(", "message=", "setWindowTitle")

_APP = None


def _app():
    global _APP
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(["pytest-ui-design-rules"])
    _APP = app
    return app


def test_dialogs_have_no_per_dialog_stylesheet():
    offenders = []
    for path in list(DIALOGS_DIR.glob("*.py")) + [FALLBACKS]:
        if path.name in ("styles.py", "__init__.py"):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "setStyleSheet" in line:
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, "per-dialog QSS remains:\n" + "\n".join(offenders)


def test_dialogs_do_not_pin_dark_stylesheet():
    from upbit_autotrader.ui.dialogs import styles

    assert styles.DARK_STYLESHEET  # kept as a deprecated alias
    offenders = []
    for path in list(DIALOGS_DIR.glob("*.py")) + [FALLBACKS]:
        if path.name in ("styles.py", "__init__.py"):
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "DARK_STYLESHEET" in line:
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, "pinned dark stylesheet remains:\n" + "\n".join(offenders)


def test_dialog_stylesheet_follows_os_theme():
    from upbit_autotrader.ui.dialogs import styles
    from upbit_autotrader.ui.theme import build_stylesheet, is_dark_mode

    assert styles.dialog_stylesheet() == build_stylesheet(is_dark_mode())


def test_stat_cards_use_theme_property_not_inline_qss():
    _app()
    from types import SimpleNamespace

    from upbit_autotrader.controllers.ui_parts import dashboard_ops
    from upbit_autotrader.ui.theme import build_stylesheet

    host = SimpleNamespace(reset_statistics=lambda: None)
    widget = dashboard_ops.create_statistics_tab(host)
    assert widget is not None
    for name in ("stat_trades", "stat_winrate", "stat_profit", "stat_holdings"):
        label = getattr(host, name)
        assert label.property("statCard") is True, name
        assert label.styleSheet() == "", name
    for dark in (True, False):
        assert 'statCard="true"' in build_stylesheet(dark)


def test_chart_colors_reuse_design_tokens():
    from upbit_autotrader.controllers.ui_parts import trading_view_ops
    from upbit_autotrader.ui import design_tokens as tokens

    assert trading_view_ops.UP_COLOR == tokens.TRADE_BUY
    assert trading_view_ops.DOWN_COLOR == tokens.TRADE_SELL


def test_no_emoji_in_widget_visible_strings():
    offenders = []
    root = REPO / "upbit_autotrader"
    for path in sorted(root.rglob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(t in line for t in _UI_LINE_TRIGGERS) and _EMOJI_RE.search(line):
                offenders.append(f"{path.relative_to(REPO)}:{lineno}")
    assert not offenders, "emoji in widget-visible strings:\n" + "\n".join(offenders)


def test_preset_feedback_prefers_infobar_over_modal():
    from upbit_autotrader.ui.dialogs import preset as preset_mod

    assert callable(preset_mod.PresetManagerDialog._feedback)
    # destructive delete-confirm stays a blocking question
    source = (DIALOGS_DIR / "preset.py").read_text(encoding="utf-8")
    assert "QMessageBox.question" in source
    assert "notify_or_fallback" in source


def test_preset_empty_name_uses_feedback_fallback_headless():
    _app()
    from unittest.mock import patch

    from PyQt6.QtWidgets import QMessageBox

    from upbit_autotrader.ui.dialogs.preset import PresetManagerDialog

    dialog = PresetManagerDialog(parent=None, current_values={})
    dialog.input_name.setText("   ")
    with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Ok) as warn:
        dialog.save_current_preset()
    assert warn.call_count == 1
    dialog.close()
