import os
import sys
import winreg
from typing import Any, cast

from PyQt6.QtWidgets import QMessageBox

from upbit_autotrader.core.config import Config
from upbit_autotrader.controllers._type_support import ControllerTypeBase
from upbit_autotrader.controllers.settings_field_specs import apply_settings_to_widgets, collect_settings_from_specs
try:
    from upbit_autotrader.notifications.notifiers import EventType, UpbitNotificationManager
except ImportError:
    EventType = cast(Any, None)
    UpbitNotificationManager = cast(Any, None)
from upbit_autotrader.services.settings_store import load_settings as load_settings_v2, save_settings as save_settings_v2


class TraderSettingsController(ControllerTypeBase):
    def save_settings(self):
        """설정 저장"""
        settings = collect_settings_from_specs(self, Config)
        settings["access_key"] = self.input_access.text().strip()
        settings["secret_key"] = self.input_secret.text().strip()
        settings["system"] = self.system_settings

        if hasattr(self, "chk_use_cooldown"):
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
            self.configure_runtime_integrations()
            self.log("✅ 설정이 저장되었습니다")
        except Exception as e:
            self.log(f"[ERROR] 설정 저장 실패: {e}")

    def load_settings(self):
        """설정 불러오기"""
        try:
            s = load_settings_v2(Config.SETTINGS_FILE)
            if not s:
                return

            apply_settings_to_widgets(self, s, Config)
            if hasattr(self, "spin_price_feed_stale_sec"):
                self.spin_price_feed_stale_sec.setValue(int(s.get("price_feed_stale_sec", Config.DEFAULT_PRICE_FEED_STALE_SEC)))
            if hasattr(self, "spin_portfolio_corr_window"):
                self.spin_portfolio_corr_window.setValue(int(s.get("portfolio_corr_window", Config.DEFAULT_PORTFOLIO_CORR_WINDOW)))
            if hasattr(self, "spin_twap_slices"):
                self.spin_twap_slices.setValue(int(s.get("twap_slices", Config.DEFAULT_TWAP_SLICES)))
            if hasattr(self, "spin_twap_interval_sec"):
                self.spin_twap_interval_sec.setValue(int(s.get("twap_interval_sec", Config.DEFAULT_TWAP_INTERVAL_SEC)))
            if hasattr(self, "spin_meta_score_threshold"):
                self.spin_meta_score_threshold.setValue(float(s.get("meta_score_threshold", Config.DEFAULT_META_SCORE_THRESHOLD)))
            if hasattr(self, "spin_paper_seed_krw"):
                self.spin_paper_seed_krw.setValue(float(s.get("paper_seed_krw", Config.DEFAULT_PAPER_SEED_KRW)))

            if hasattr(self, "chk_use_cooldown"):
                self.chk_use_cooldown.setChecked(s.get("use_cooldown", self.advanced_settings["use_cooldown"]))
                self.spin_cooldown.setValue(s.get("cooldown_minutes", self.advanced_settings["cooldown_minutes"]))
                self.chk_use_time_exit.setChecked(s.get("use_time_exit", self.advanced_settings["use_time_exit"]))
                self.spin_max_holding_hours.setValue(
                    s.get("max_holding_hours", self.advanced_settings["max_holding_hours"])
                )
                self.chk_use_dynamic_position.setChecked(
                    s.get("use_dynamic_position", self.advanced_settings["use_dynamic_position"])
                )
                self.chk_use_mtf.setChecked(s.get("use_mtf", self.advanced_settings["use_mtf"]))
                self.chk_use_gap.setChecked(s.get("use_gap_analysis", self.advanced_settings["use_gap_analysis"]))
                self.chk_use_breakout_confirm.setChecked(
                    s.get("use_breakout_confirm", self.advanced_settings["use_breakout_confirm"])
                )
                self.spin_breakout_ticks.setValue(
                    s.get("breakout_confirm_ticks", self.advanced_settings["breakout_confirm_ticks"])
                )

            if "system" in s:
                self.system_settings.update(s["system"])

            self.input_access.setText(s.get("access_key", ""))
            self.input_secret.setText(s.get("secret_key", ""))

            credential_error = s.get("_credential_error")
            if credential_error:
                self.log(f"[WARN] API 키 복호화 실패: {credential_error}")
                self.send_notification("Upbit Pro Trader", "저장된 API 키를 복호화하지 못했습니다.")

            self.configure_runtime_integrations()
            self.log("📂 저장된 설정을 불러왔습니다")
            if hasattr(self, "refresh_trade_action_buttons"):
                self.refresh_trade_action_buttons()
        except Exception as e:
            self.log(f"[WARN] 설정 불러오기 실패: {e}")

    def configure_runtime_integrations(self):
        """알림/복구 관련 런타임 통합 설정 적용."""
        try:
            persist = bool(
                self.chk_persist_reconciliation_state.isChecked()
                if hasattr(self, "chk_persist_reconciliation_state")
                else Config.DEFAULT_PERSIST_RECONCILIATION_STATE
            )
            self.persist_reconciliation_state = persist
        except Exception:
            self.persist_reconciliation_state = bool(Config.DEFAULT_PERSIST_RECONCILIATION_STATE)

        if UpbitNotificationManager is None or EventType is None:
            return

        manager = getattr(self, "notification_manager", None)
        if manager is None:
            manager = UpbitNotificationManager()
            self.notification_manager = manager

        enabled = bool(
            self.chk_enable_discord_alerts.isChecked()
            if hasattr(self, "chk_enable_discord_alerts")
            else Config.DEFAULT_ENABLE_DISCORD_ALERTS
        )
        webhook = ""
        if hasattr(self, "input_discord_webhook"):
            webhook = self.input_discord_webhook.text().strip()

        if enabled and webhook:
            manager.configure_discord(
                webhook,
                events=[
                    EventType.BUY,
                    EventType.SELL,
                    EventType.WARNING,
                    EventType.ERROR,
                    EventType.EMERGENCY,
                ],
            )
        else:
            manager.discord = None
            manager.event_filters.pop("discord", None)

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


