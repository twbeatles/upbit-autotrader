from PyQt6.QtWidgets import QVBoxLayout, QWidget

from upbit_autotrader.controllers.ui_parts.advanced_tab import (
    alert_group,
    execution_group,
    filter_groups,
    legacy_advanced_groups,
    market_regime_group,
    meta_group,
    paper_group,
    preset_group,
    risk_groups,
    sizing_group,
    strategy_engine_group,
)
from upbit_autotrader.controllers.ui_parts.ops_tab import build_ops_tab


def build_advanced_tab(self):
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setSpacing(15)
    layout.setContentsMargins(15, 15, 15, 15)

    for group in (
        filter_groups.build_rsi_group(self),
        filter_groups.build_macd_group(self),
        filter_groups.build_volume_group(self),
        risk_groups.build_risk_group(self),
        strategy_engine_group.build_strategy_engine_group(self),
        paper_group.build_paper_group(self),
        sizing_group.build_sizing_group(self),
        execution_group.build_execution_group(self),
        market_regime_group.build_market_regime_group(self),
        meta_group.build_meta_group(self),
        alert_group.build_alert_group(self),
    ):
        layout.addWidget(group)

    for group in legacy_advanced_groups.build_legacy_advanced_groups(self):
        layout.addWidget(group)

    layout.addWidget(preset_group.build_preset_group(self))
    layout.addStretch(1)
    return widget
