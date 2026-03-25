from typing import Any, cast


Config = cast(Any, None)
QDialog = cast(Any, None)
PresetManagerDialog = cast(Any, None)
PresetManagerDialogV3 = cast(Any, None)
HelpDialog = cast(Any, None)
HelpDialogV3 = cast(Any, None)
SettingsDialog = cast(Any, None)
SettingsDialogV3 = cast(Any, None)


def bind_runtime(**kwargs):
    globals().update(kwargs)


def open_preset_manager(self):
    current_values = {
        "k": self.spin_k.value(),
        "ts_start": self.spin_ts_start.value(),
        "ts_stop": self.spin_ts_stop.value(),
        "loss": self.spin_loss.value(),
        "betting": self.spin_betting.value(),
        "rsi_upper": self.spin_rsi_upper.value(),
        "max_holdings": self.spin_max_holdings.value(),
        "use_strategy_engine": self.chk_use_strategy_engine.isChecked() if hasattr(self, "chk_use_strategy_engine") else Config.DEFAULT_USE_STRATEGY_ENGINE,
        "strategy_mode": self.combo_strategy_mode.currentData() if hasattr(self, "combo_strategy_mode") else Config.DEFAULT_STRATEGY_MODE,
        "single_strategy": self.combo_single_strategy.currentData() if hasattr(self, "combo_single_strategy") else Config.DEFAULT_SINGLE_STRATEGY,
        "engine_gate_policy": self.combo_engine_gate_policy.currentData() if hasattr(self, "combo_engine_gate_policy") else Config.DEFAULT_ENGINE_GATE_POLICY,
        "ensemble_threshold": self.spin_ensemble_threshold.value() if hasattr(self, "spin_ensemble_threshold") else Config.DEFAULT_ENSEMBLE_THRESHOLD,
        "active_strategies": self.input_active_strategies.text().strip() if hasattr(self, "input_active_strategies") else ",".join(Config.DEFAULT_ACTIVE_STRATEGIES),
        "strategy_weights": self.input_strategy_weights.text().strip() if hasattr(self, "input_strategy_weights") else "",
        "paper_trading": self.chk_paper_trading.isChecked() if hasattr(self, "chk_paper_trading") else Config.DEFAULT_PAPER_TRADING,
        "paper_allow_without_login": self.chk_paper_allow_without_login.isChecked() if hasattr(self, "chk_paper_allow_without_login") else Config.DEFAULT_PAPER_ALLOW_WITHOUT_LOGIN,
        "paper_seed_krw": self.spin_paper_seed_krw.value() if hasattr(self, "spin_paper_seed_krw") else Config.DEFAULT_PAPER_SEED_KRW,
        "paper_fee_bps": self.spin_paper_fee_bps.value() if hasattr(self, "spin_paper_fee_bps") else Config.DEFAULT_PAPER_FEE_BPS,
        "paper_slippage_bps": self.spin_paper_slippage_bps.value() if hasattr(self, "spin_paper_slippage_bps") else Config.DEFAULT_PAPER_SLIPPAGE_BPS,
        "enable_account_wide_sync": self.chk_enable_account_wide_sync.isChecked() if hasattr(self, "chk_enable_account_wide_sync") else Config.DEFAULT_ENABLE_ACCOUNT_WIDE_SYNC,
        "risk_include_unrealized": self.chk_risk_include_unrealized.isChecked() if hasattr(self, "chk_risk_include_unrealized") else Config.DEFAULT_RISK_INCLUDE_UNREALIZED,
        "risk_include_external_holdings": self.chk_risk_include_external_holdings.isChecked() if hasattr(self, "chk_risk_include_external_holdings") else Config.DEFAULT_RISK_INCLUDE_EXTERNAL_HOLDINGS,
        "manual_review_on_timeout": self.chk_manual_review_on_timeout.isChecked() if hasattr(self, "chk_manual_review_on_timeout") else Config.DEFAULT_MANUAL_REVIEW_ON_TIMEOUT,
        "price_feed_stale_sec": self.spin_price_feed_stale_sec.value() if hasattr(self, "spin_price_feed_stale_sec") else Config.DEFAULT_PRICE_FEED_STALE_SEC,
    }
    dialog_cls = PresetManagerDialogV3 if PresetManagerDialogV3 else PresetManagerDialog
    dialog = dialog_cls(self, current_values)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        preset = dialog.get_selected_preset()
        if preset:
            self.apply_preset_values(preset)


def apply_preset_values(self, preset):
    for key, widget in (
        ("k", getattr(self, "spin_k", None)),
        ("ts_start", getattr(self, "spin_ts_start", None)),
        ("ts_stop", getattr(self, "spin_ts_stop", None)),
        ("loss", getattr(self, "spin_loss", None)),
        ("betting", getattr(self, "spin_betting", None)),
        ("rsi_upper", getattr(self, "spin_rsi_upper", None)),
        ("max_holdings", getattr(self, "spin_max_holdings", None)),
    ):
        if key in preset and widget is not None:
            widget.setValue(preset[key])
    if hasattr(self, "chk_use_strategy_engine") and "use_strategy_engine" in preset:
        self.chk_use_strategy_engine.setChecked(bool(preset["use_strategy_engine"]))
    if hasattr(self, "combo_strategy_mode") and "strategy_mode" in preset:
        idx = self.combo_strategy_mode.findData(preset["strategy_mode"])
        if idx >= 0:
            self.combo_strategy_mode.setCurrentIndex(idx)
    if hasattr(self, "combo_single_strategy") and "single_strategy" in preset:
        idx = self.combo_single_strategy.findData(preset["single_strategy"])
        if idx >= 0:
            self.combo_single_strategy.setCurrentIndex(idx)
    if hasattr(self, "combo_engine_gate_policy") and "engine_gate_policy" in preset:
        idx = self.combo_engine_gate_policy.findData(preset["engine_gate_policy"])
        if idx >= 0:
            self.combo_engine_gate_policy.setCurrentIndex(idx)
    if hasattr(self, "spin_ensemble_threshold") and "ensemble_threshold" in preset:
        self.spin_ensemble_threshold.setValue(int(preset["ensemble_threshold"]))
    if hasattr(self, "input_active_strategies") and "active_strategies" in preset:
        self.input_active_strategies.setText(str(preset["active_strategies"]))
    if hasattr(self, "input_strategy_weights") and "strategy_weights" in preset:
        self.input_strategy_weights.setText(str(preset["strategy_weights"]))
    if hasattr(self, "chk_paper_trading") and "paper_trading" in preset:
        self.chk_paper_trading.setChecked(bool(preset["paper_trading"]))
    if hasattr(self, "chk_paper_allow_without_login") and "paper_allow_without_login" in preset:
        self.chk_paper_allow_without_login.setChecked(bool(preset["paper_allow_without_login"]))
    if hasattr(self, "spin_paper_seed_krw") and "paper_seed_krw" in preset:
        self.spin_paper_seed_krw.setValue(float(preset["paper_seed_krw"]))
    if hasattr(self, "spin_paper_fee_bps") and "paper_fee_bps" in preset:
        self.spin_paper_fee_bps.setValue(float(preset["paper_fee_bps"]))
    if hasattr(self, "spin_paper_slippage_bps") and "paper_slippage_bps" in preset:
        self.spin_paper_slippage_bps.setValue(float(preset["paper_slippage_bps"]))
    if hasattr(self, "chk_enable_account_wide_sync") and "enable_account_wide_sync" in preset:
        self.chk_enable_account_wide_sync.setChecked(bool(preset["enable_account_wide_sync"]))
    if hasattr(self, "chk_risk_include_unrealized") and "risk_include_unrealized" in preset:
        self.chk_risk_include_unrealized.setChecked(bool(preset["risk_include_unrealized"]))
    if hasattr(self, "chk_risk_include_external_holdings") and "risk_include_external_holdings" in preset:
        self.chk_risk_include_external_holdings.setChecked(bool(preset["risk_include_external_holdings"]))
    if hasattr(self, "chk_manual_review_on_timeout") and "manual_review_on_timeout" in preset:
        self.chk_manual_review_on_timeout.setChecked(bool(preset["manual_review_on_timeout"]))
    if hasattr(self, "spin_price_feed_stale_sec") and "price_feed_stale_sec" in preset:
        self.spin_price_feed_stale_sec.setValue(int(preset["price_feed_stale_sec"]))

    name = preset.get("name", "사용자 정의")
    self.lbl_current_preset.setText(f"✅ 현재 프리셋: {name}")
    self.log(f"📋 {name} 프리셋 적용됨")
    self.refresh_trade_action_buttons()


def _paper_no_login_allowed(self):
    if not hasattr(self, "chk_paper_trading") or not self.chk_paper_trading.isChecked():
        return False
    if hasattr(self, "chk_paper_allow_without_login"):
        return bool(self.chk_paper_allow_without_login.isChecked())
    return bool(Config.DEFAULT_PAPER_ALLOW_WITHOUT_LOGIN)


def refresh_trade_action_buttons(self):
    connected = bool(getattr(self, "is_connected", False) and getattr(self, "upbit", None))
    enabled = connected or _paper_no_login_allowed(self)
    for attr in ("btn_start", "btn_batch_buy", "btn_batch_sell"):
        btn = getattr(self, attr, None)
        if btn is not None:
            btn.setEnabled(enabled)


def show_help(self):
    dialog_cls = HelpDialogV3 if HelpDialogV3 else HelpDialog
    dialog = dialog_cls(self)
    dialog.exec()


def show_settings(self):
    dialog_cls = SettingsDialogV3 if SettingsDialogV3 else SettingsDialog
    dialog = dialog_cls(self, self.system_settings)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        new_settings = dialog.get_settings()
        if new_settings["run_at_startup"] != self.system_settings.get("run_at_startup", False):
            self.set_startup_registry(new_settings["run_at_startup"])
        self.system_settings.update(new_settings)
        self.save_settings()
        self.log("⚙️ 시스템 설정이 저장되었습니다")
