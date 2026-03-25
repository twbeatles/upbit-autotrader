from PyQt6.QtWidgets import QCheckBox, QGridLayout, QGroupBox, QLabel, QLineEdit

from upbit_autotrader.core.config import Config


def build_alert_group(self):
    group = QGroupBox("🔔 운영 알림 채널")
    layout = QGridLayout()
    self.chk_enable_discord_alerts = QCheckBox("Discord 알림 사용")
    self.chk_enable_discord_alerts.setChecked(Config.DEFAULT_ENABLE_DISCORD_ALERTS)
    self.chk_enable_discord_alerts.setToolTip(Config.TOOLTIPS.get("discord_alerts", ""))
    layout.addWidget(self.chk_enable_discord_alerts, 0, 0, 1, 2)

    layout.addWidget(QLabel("Discord Webhook:"), 1, 0)
    self.input_discord_webhook = QLineEdit(Config.DEFAULT_DISCORD_WEBHOOK)
    self.input_discord_webhook.setPlaceholderText("https://discord.com/api/webhooks/...")
    layout.addWidget(self.input_discord_webhook, 1, 1, 1, 5)
    group.setLayout(layout)
    return group
