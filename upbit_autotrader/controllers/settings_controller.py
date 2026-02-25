import os
import sys
import winreg

from PyQt6.QtWidgets import QMessageBox

from upbit_config import Config
from upbit_settings_store import load_settings as load_settings_v2, save_settings as save_settings_v2


class TraderSettingsController:
    def save_settings(self):
        """설정 저장"""
        settings = {
            "coins": self.input_coins.text(),
            "candle": self.combo_candle.currentText(),
            "betting_ratio": self.spin_betting.value(),
            "k_value": self.spin_k.value(),
            "ts_start": self.spin_ts_start.value(),
            "ts_stop": self.spin_ts_stop.value(),
            "loss_cut": self.spin_loss.value(),
            "use_rsi": self.chk_use_rsi.isChecked(),
            "rsi_upper": self.spin_rsi_upper.value(),
            "rsi_period": self.spin_rsi_period.value(),
            "use_volume": self.chk_use_volume.isChecked(),
            "volume_mult": self.spin_volume_mult.value(),
            "use_risk": self.chk_use_risk.isChecked(),
            "max_daily_loss": self.spin_max_loss.value(),
            "max_holdings": self.spin_max_holdings.value(),
            "use_partial_tp": self.chk_use_partial_tp.isChecked(),
            "use_entry_scoring": self.chk_use_entry_scoring.isChecked(),
            "entry_score_threshold": self.spin_entry_score_threshold.value(),
            "use_strategy_engine": self.chk_use_strategy_engine.isChecked() if hasattr(self, "chk_use_strategy_engine") else Config.DEFAULT_USE_STRATEGY_ENGINE,
            "strategy_mode": self.combo_strategy_mode.currentData() if hasattr(self, "combo_strategy_mode") else Config.DEFAULT_STRATEGY_MODE,
            "single_strategy": self.combo_single_strategy.currentData() if hasattr(self, "combo_single_strategy") else Config.DEFAULT_SINGLE_STRATEGY,
            "engine_gate_policy": self.combo_engine_gate_policy.currentData() if hasattr(self, "combo_engine_gate_policy") else Config.DEFAULT_ENGINE_GATE_POLICY,
            "ensemble_threshold": self.spin_ensemble_threshold.value() if hasattr(self, "spin_ensemble_threshold") else Config.DEFAULT_ENSEMBLE_THRESHOLD,
            "active_strategies": self.input_active_strategies.text().strip() if hasattr(self, "input_active_strategies") else ",".join(Config.DEFAULT_ACTIVE_STRATEGIES),
            "strategy_weights": self.input_strategy_weights.text().strip() if hasattr(self, "input_strategy_weights") else "",
            "use_volatility_targeting": self.chk_use_volatility_targeting.isChecked() if hasattr(self, "chk_use_volatility_targeting") else Config.DEFAULT_USE_VOLATILITY_TARGETING,
            "target_vol_pct": self.spin_target_vol.value() if hasattr(self, "spin_target_vol") else Config.DEFAULT_TARGET_VOL_PCT,
            "use_regime_filter": self.chk_use_regime_filter.isChecked() if hasattr(self, "chk_use_regime_filter") else Config.DEFAULT_USE_REGIME_FILTER,
            "regime_min_adx": self.spin_regime_min_adx.value() if hasattr(self, "spin_regime_min_adx") else Config.DEFAULT_REGIME_MIN_ADX,
            "use_drawdown_guard": self.chk_use_drawdown_guard.isChecked() if hasattr(self, "chk_use_drawdown_guard") else Config.DEFAULT_USE_DRAWDOWN_GUARD,
            "drawdown_guard_pct": self.spin_drawdown_guard.value() if hasattr(self, "spin_drawdown_guard") else Config.DEFAULT_DRAWDOWN_GUARD_PCT,
            "max_consecutive_losses": self.spin_max_consecutive_losses.value() if hasattr(self, "spin_max_consecutive_losses") else Config.DEFAULT_MAX_CONSECUTIVE_LOSSES,
            "enable_account_wide_sync": self.chk_enable_account_wide_sync.isChecked() if hasattr(self, "chk_enable_account_wide_sync") else Config.DEFAULT_ENABLE_ACCOUNT_WIDE_SYNC,
            "risk_include_unrealized": self.chk_risk_include_unrealized.isChecked() if hasattr(self, "chk_risk_include_unrealized") else Config.DEFAULT_RISK_INCLUDE_UNREALIZED,
            "risk_include_external_holdings": self.chk_risk_include_external_holdings.isChecked() if hasattr(self, "chk_risk_include_external_holdings") else Config.DEFAULT_RISK_INCLUDE_EXTERNAL_HOLDINGS,
            "price_feed_stale_sec": self.spin_price_feed_stale_sec.value() if hasattr(self, "spin_price_feed_stale_sec") else Config.DEFAULT_PRICE_FEED_STALE_SEC,
            "manual_review_on_timeout": self.chk_manual_review_on_timeout.isChecked() if hasattr(self, "chk_manual_review_on_timeout") else Config.DEFAULT_MANUAL_REVIEW_ON_TIMEOUT,
            "paper_trading": self.chk_paper_trading.isChecked() if hasattr(self, "chk_paper_trading") else Config.DEFAULT_PAPER_TRADING,
            "paper_allow_without_login": self.chk_paper_allow_without_login.isChecked() if hasattr(self, "chk_paper_allow_without_login") else Config.DEFAULT_PAPER_ALLOW_WITHOUT_LOGIN,
            "paper_seed_krw": self.spin_paper_seed_krw.value() if hasattr(self, "spin_paper_seed_krw") else Config.DEFAULT_PAPER_SEED_KRW,
            "paper_fee_bps": self.spin_paper_fee_bps.value() if hasattr(self, "spin_paper_fee_bps") else Config.DEFAULT_PAPER_FEE_BPS,
            "paper_slippage_bps": self.spin_paper_slippage_bps.value() if hasattr(self, "spin_paper_slippage_bps") else Config.DEFAULT_PAPER_SLIPPAGE_BPS,
            # API 키 저장 (DPAPI 암호화 저장소로 전달)
            "access_key": self.input_access.text().strip(),
            "secret_key": self.input_secret.text().strip(),
            # 시스템 설정
            "system": self.system_settings
        }

        if hasattr(self, 'chk_use_cooldown'):
            settings["use_cooldown"] = self.chk_use_cooldown.isChecked()
            settings["cooldown_minutes"] = self.spin_cooldown.value()
            settings["use_time_exit"] = self.chk_use_time_exit.isChecked()
            settings["max_holding_hours"] = self.spin_max_holding_hours.value()
            settings["use_dynamic_position"] = self.chk_use_dynamic_position.isChecked()
            settings["use_mtf"] = self.chk_use_mtf.isChecked()
            settings["use_gap_analysis"] = self.chk_use_gap.isChecked()
            settings["use_breakout_confirm"] = self.chk_use_breakout_confirm.isChecked()
            settings["breakout_confirm_ticks"] = self.spin_breakout_ticks.value()
        
        try:
            save_settings_v2(Config.SETTINGS_FILE, settings)
            self.log("✅ 설정이 저장되었습니다")
        except Exception as e:
            self.log(f"[ERROR] 설정 저장 실패: {e}")

    def load_settings(self):
        """설정 불러오기"""
        try:
            s = load_settings_v2(Config.SETTINGS_FILE)
            if not s:
                return

            self.input_coins.setText(s.get("coins", Config.DEFAULT_COINS))
            self.combo_candle.setCurrentText(s.get("candle", Config.DEFAULT_CANDLE))
            self.spin_betting.setValue(s.get("betting_ratio", Config.DEFAULT_BETTING_RATIO))
            self.spin_k.setValue(s.get("k_value", Config.DEFAULT_K_VALUE))
            self.spin_ts_start.setValue(s.get("ts_start", Config.DEFAULT_TS_START))
            self.spin_ts_stop.setValue(s.get("ts_stop", Config.DEFAULT_TS_STOP))
            self.spin_loss.setValue(s.get("loss_cut", Config.DEFAULT_LOSS_CUT))
            self.chk_use_rsi.setChecked(s.get("use_rsi", Config.DEFAULT_USE_RSI))
            self.spin_rsi_upper.setValue(s.get("rsi_upper", Config.DEFAULT_RSI_UPPER))
            self.spin_rsi_period.setValue(s.get("rsi_period", Config.DEFAULT_RSI_PERIOD))
            self.chk_use_volume.setChecked(s.get("use_volume", Config.DEFAULT_USE_VOLUME))
            self.spin_volume_mult.setValue(s.get("volume_mult", Config.DEFAULT_VOLUME_MULTIPLIER))
            self.chk_use_risk.setChecked(s.get("use_risk", Config.DEFAULT_USE_RISK_MGMT))
            self.spin_max_loss.setValue(s.get("max_daily_loss", Config.DEFAULT_MAX_DAILY_LOSS))
            self.spin_max_holdings.setValue(s.get("max_holdings", Config.DEFAULT_MAX_HOLDINGS))
            self.chk_use_partial_tp.setChecked(s.get("use_partial_tp", False))
            self.chk_use_entry_scoring.setChecked(s.get("use_entry_scoring", False))
            self.spin_entry_score_threshold.setValue(s.get("entry_score_threshold", Config.ENTRY_SCORE_THRESHOLD))
            if hasattr(self, "chk_use_strategy_engine"):
                self.chk_use_strategy_engine.setChecked(s.get("use_strategy_engine", Config.DEFAULT_USE_STRATEGY_ENGINE))
            if hasattr(self, "combo_strategy_mode"):
                mode = s.get("strategy_mode", Config.DEFAULT_STRATEGY_MODE)
                idx = self.combo_strategy_mode.findData(mode)
                if idx >= 0:
                    self.combo_strategy_mode.setCurrentIndex(idx)
            if hasattr(self, "combo_single_strategy"):
                sid = s.get("single_strategy", Config.DEFAULT_SINGLE_STRATEGY)
                idx = self.combo_single_strategy.findData(sid)
                if idx >= 0:
                    self.combo_single_strategy.setCurrentIndex(idx)
            if hasattr(self, "combo_engine_gate_policy"):
                gate = s.get("engine_gate_policy", Config.DEFAULT_ENGINE_GATE_POLICY)
                idx = self.combo_engine_gate_policy.findData(gate)
                if idx >= 0:
                    self.combo_engine_gate_policy.setCurrentIndex(idx)
            if hasattr(self, "spin_ensemble_threshold"):
                self.spin_ensemble_threshold.setValue(s.get("ensemble_threshold", Config.DEFAULT_ENSEMBLE_THRESHOLD))
            if hasattr(self, "input_active_strategies"):
                self.input_active_strategies.setText(s.get("active_strategies", ",".join(Config.DEFAULT_ACTIVE_STRATEGIES)))
            if hasattr(self, "input_strategy_weights"):
                self.input_strategy_weights.setText(s.get("strategy_weights", ""))
            if hasattr(self, "chk_use_volatility_targeting"):
                self.chk_use_volatility_targeting.setChecked(s.get("use_volatility_targeting", Config.DEFAULT_USE_VOLATILITY_TARGETING))
            if hasattr(self, "spin_target_vol"):
                self.spin_target_vol.setValue(s.get("target_vol_pct", Config.DEFAULT_TARGET_VOL_PCT))
            if hasattr(self, "chk_use_regime_filter"):
                self.chk_use_regime_filter.setChecked(s.get("use_regime_filter", Config.DEFAULT_USE_REGIME_FILTER))
            if hasattr(self, "spin_regime_min_adx"):
                self.spin_regime_min_adx.setValue(s.get("regime_min_adx", Config.DEFAULT_REGIME_MIN_ADX))
            if hasattr(self, "chk_use_drawdown_guard"):
                self.chk_use_drawdown_guard.setChecked(s.get("use_drawdown_guard", Config.DEFAULT_USE_DRAWDOWN_GUARD))
            if hasattr(self, "spin_drawdown_guard"):
                self.spin_drawdown_guard.setValue(s.get("drawdown_guard_pct", Config.DEFAULT_DRAWDOWN_GUARD_PCT))
            if hasattr(self, "spin_max_consecutive_losses"):
                self.spin_max_consecutive_losses.setValue(s.get("max_consecutive_losses", Config.DEFAULT_MAX_CONSECUTIVE_LOSSES))
            if hasattr(self, "chk_enable_account_wide_sync"):
                self.chk_enable_account_wide_sync.setChecked(s.get("enable_account_wide_sync", Config.DEFAULT_ENABLE_ACCOUNT_WIDE_SYNC))
            if hasattr(self, "chk_risk_include_unrealized"):
                self.chk_risk_include_unrealized.setChecked(s.get("risk_include_unrealized", Config.DEFAULT_RISK_INCLUDE_UNREALIZED))
            if hasattr(self, "chk_risk_include_external_holdings"):
                self.chk_risk_include_external_holdings.setChecked(
                    s.get("risk_include_external_holdings", Config.DEFAULT_RISK_INCLUDE_EXTERNAL_HOLDINGS)
                )
            if hasattr(self, "spin_price_feed_stale_sec"):
                self.spin_price_feed_stale_sec.setValue(int(s.get("price_feed_stale_sec", Config.DEFAULT_PRICE_FEED_STALE_SEC)))
            if hasattr(self, "chk_manual_review_on_timeout"):
                self.chk_manual_review_on_timeout.setChecked(
                    s.get("manual_review_on_timeout", Config.DEFAULT_MANUAL_REVIEW_ON_TIMEOUT)
                )
            if hasattr(self, "chk_paper_trading"):
                self.chk_paper_trading.setChecked(s.get("paper_trading", Config.DEFAULT_PAPER_TRADING))
            if hasattr(self, "chk_paper_allow_without_login"):
                self.chk_paper_allow_without_login.setChecked(s.get("paper_allow_without_login", Config.DEFAULT_PAPER_ALLOW_WITHOUT_LOGIN))
            if hasattr(self, "spin_paper_seed_krw"):
                self.spin_paper_seed_krw.setValue(float(s.get("paper_seed_krw", Config.DEFAULT_PAPER_SEED_KRW)))
            if hasattr(self, "spin_paper_fee_bps"):
                self.spin_paper_fee_bps.setValue(s.get("paper_fee_bps", Config.DEFAULT_PAPER_FEE_BPS))
            if hasattr(self, "spin_paper_slippage_bps"):
                self.spin_paper_slippage_bps.setValue(s.get("paper_slippage_bps", Config.DEFAULT_PAPER_SLIPPAGE_BPS))

            if hasattr(self, 'chk_use_cooldown'):
                self.chk_use_cooldown.setChecked(s.get("use_cooldown", self.advanced_settings['use_cooldown']))
                self.spin_cooldown.setValue(s.get("cooldown_minutes", self.advanced_settings['cooldown_minutes']))
                self.chk_use_time_exit.setChecked(s.get("use_time_exit", self.advanced_settings['use_time_exit']))
                self.spin_max_holding_hours.setValue(
                    s.get("max_holding_hours", self.advanced_settings['max_holding_hours'])
                )
                self.chk_use_dynamic_position.setChecked(
                    s.get("use_dynamic_position", self.advanced_settings['use_dynamic_position'])
                )
                self.chk_use_mtf.setChecked(s.get("use_mtf", self.advanced_settings['use_mtf']))
                self.chk_use_gap.setChecked(s.get("use_gap_analysis", self.advanced_settings['use_gap_analysis']))
                self.chk_use_breakout_confirm.setChecked(
                    s.get("use_breakout_confirm", self.advanced_settings['use_breakout_confirm'])
                )
                self.spin_breakout_ticks.setValue(
                    s.get("breakout_confirm_ticks", self.advanced_settings['breakout_confirm_ticks'])
                )

            # 시스템 설정 불러오기
            if "system" in s:
                self.system_settings.update(s["system"])

            self.input_access.setText(s.get("access_key", ""))
            self.input_secret.setText(s.get("secret_key", ""))

            credential_error = s.get("_credential_error")
            if credential_error:
                self.log(f"[WARN] API 키 복호화 실패: {credential_error}")
                self.send_notification("Upbit Pro Trader", "저장된 API 키를 복호화하지 못했습니다.")

            self.log("📂 저장된 설정을 불러왔습니다")
            if hasattr(self, "refresh_trade_action_buttons"):
                self.refresh_trade_action_buttons()
        except Exception as e:
            self.log(f"[WARN] 설정 불러오기 실패: {e}")

    # ------------------------------------------------------------------
    # 로그인 및 잔고
    # ------------------------------------------------------------------

    def set_startup_registry(self, enable):
        """Windows 시작 프로그램 레지스트리 설정"""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "UpbitProTrader"
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            
            if enable:
                # 현재 실행 파일 경로
                exe_path = sys.executable
                if getattr(sys, 'frozen', False):
                    exe_path = sys.executable
                else:
                    exe_path = os.path.abspath(sys.argv[0])
                
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{exe_path}"')
                self.log("✅ Windows 시작 시 자동 실행이 설정되었습니다")
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                    self.log("❌ Windows 시작 시 자동 실행이 해제되었습니다")
                except FileNotFoundError:
                    pass
            
            winreg.CloseKey(key)
        except Exception as e:
            self.logger.error(f"레지스트리 설정 실패: {e}")

    def send_notification(self, title, message):
        """트레이 알림 표시"""
        if not self.system_settings.get('show_tray_notifications', True):
            return

        tray_icon = getattr(self, "tray_icon", None)
        if tray_icon is None or not hasattr(tray_icon, "showMessage"):
            return

        try:
            message_icon = None
            if hasattr(tray_icon, "MessageIcon") and hasattr(tray_icon.MessageIcon, "Information"):
                message_icon = tray_icon.MessageIcon.Information
            if message_icon is None:
                tray_icon.showMessage(title, message)
            else:
                tray_icon.showMessage(title, message, message_icon, 3000)
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.warning(f"트레이 알림 실패: {e}")

    def check_first_run(self):
        """처음 실행 시 가이드 표시"""
        if not os.path.exists(Config.SETTINGS_FILE):
            reply = QMessageBox.question(self, "환영합니다! 👋",
                "Upbit Pro Algo-Trader에 오신 것을 환영합니다!\n\n"
                "처음 사용이시라면 빠른 시작 가이드를 \n"
                "확인하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.show_help()

