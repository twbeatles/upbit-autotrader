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
        if self.system_settings.get('show_tray_notifications', True):
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)

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

