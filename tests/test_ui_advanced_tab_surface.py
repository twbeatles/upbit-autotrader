import os

from PyQt6.QtWidgets import QApplication

from upbit_autotrader.controllers.ui_sections import build_advanced_tab

_APP = None


class _DummyLogger:
    def info(self, *_args, **_kwargs):
        return None


class _DummyUI:
    def __init__(self):
        self.strategy = object()
        self.logger = _DummyLogger()
        self.applied_presets = []
        self.refresh_calls = 0
        self.emergency_calls = 0
        self.open_preset_calls = 0

    def refresh_trade_action_buttons(self):
        self.refresh_calls += 1

    def apply_preset(self, preset_name):
        self.applied_presets.append(preset_name)

    def open_preset_manager(self):
        self.open_preset_calls += 1

    def show_emergency_dialog(self):
        self.emergency_calls += 1


def _app():
    global _APP
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if _APP is not None:
        return _APP
    app = QApplication.instance()
    if app is None:
        app = QApplication(["pytest-ui"])
    _APP = app
    return _APP


def test_build_advanced_tab_preserves_group_order_and_widget_surface():
    app = _app()
    holder = _DummyUI()
    widget = build_advanced_tab(holder)

    titles = []
    layout = widget.layout()
    for idx in range(layout.count() - 1):
        item = layout.itemAt(idx)
        child = item.widget()
        if child is not None and hasattr(child, "title"):
            titles.append(child.title())

    assert titles == [
        "📈 RSI 필터",
        "📉 MACD 필터",
        "📊 거래량 필터",
        "🛡️ 리스크 관리",
        "🧩 전략 엔진 (Single / Ensemble)",
        "🧪 페이퍼 트레이딩",
        "📐 확장 리스크/사이징",
        "⚙️ 실행 모델 / TWAP",
        "🌐 시장 레짐 / 외부 신호",
        "🧠 메타 시그널 / 가중치 리밸런싱",
        "🔔 운영 알림 채널",
        "🚀 고급 리스크 관리 (v3.0)",
        "🧠 고급 알고리즘 (v3.0)",
        "🚨 긴급 조치",
        "📋 전략 프리셋",
    ]

    required_attrs = [
        "chk_use_rsi",
        "spin_rsi_upper",
        "spin_rsi_period",
        "chk_use_macd",
        "chk_use_volume",
        "spin_volume_mult",
        "chk_use_risk",
        "spin_max_holdings",
        "chk_use_strategy_engine",
        "combo_strategy_mode",
        "combo_single_strategy",
        "chk_paper_trading",
        "spin_paper_seed_krw",
        "chk_use_risk_budget_sizing",
        "spin_risk_budget_pct",
        "chk_use_execution_model",
        "combo_execution_mode",
        "chk_use_market_regime_filter",
        "spin_market_regime_min_score",
        "chk_use_meta_signal",
        "spin_meta_score_threshold",
        "chk_enable_discord_alerts",
        "input_discord_webhook",
        "chk_use_cooldown",
        "spin_breakout_ticks",
        "btn_emergency_close",
        "lbl_current_preset",
    ]
    missing = [name for name in required_attrs if not hasattr(holder, name)]
    assert not missing, f"missing advanced-tab attrs: {missing}"
    widget.deleteLater()
    app.processEvents()
