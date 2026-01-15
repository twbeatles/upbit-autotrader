"""
Upbit Notifiers v1.0
다중 채널 알림 시스템 for Upbit Pro Algo-Trader

Discord 웹훅, Email (SMTP), 텔레그램
"""

import json
import threading
import queue
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Callable
from datetime import datetime
from enum import Enum
import logging

try:
    import requests
except ImportError:
    requests = None


class EventType(Enum):
    """알림 이벤트 유형"""
    BUY = "buy"
    SELL = "sell"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    CONNECTION = "connection"
    EMERGENCY = "emergency"


@dataclass
class NotificationConfig:
    """알림 설정"""
    discord_webhook: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    email_smtp_server: str = ""
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_to: List[str] = field(default_factory=list)


class DiscordNotifier:
    """Discord 웹훅 알림"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.enabled = bool(webhook_url)
    
    def send(self, message: str, embed: Dict = None) -> bool:
        if not self.enabled or not requests:
            return False
        
        try:
            payload = {"content": message}
            if embed:
                payload["embeds"] = [embed]
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code in [200, 204]
        except Exception as e:
            logging.warning(f"Discord 알림 실패: {e}")
            return False
    
    def send_trade_alert(self, event_type: EventType, ticker: str, 
                        price: float, pnl: float = 0) -> bool:
        """거래 알림 전송"""
        colors = {
            EventType.BUY: 0x3fb950,      # 녹색
            EventType.SELL: 0xf85149,     # 빨강
            EventType.TAKE_PROFIT: 0x00b4d8,  # 파랑
            EventType.STOP_LOSS: 0xff6b6b,    # 연빨강
        }
        
        embed = {
            "title": f"📊 {event_type.value.upper()}",
            "color": colors.get(event_type, 0x808080),
            "fields": [
                {"name": "코인", "value": ticker, "inline": True},
                {"name": "가격", "value": f"₩{price:,.0f}", "inline": True},
            ],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if pnl != 0:
            embed["fields"].append({
                "name": "손익",
                "value": f"{pnl:+.2f}%",
                "inline": True
            })
        
        return self.send("", embed)


class TelegramNotifier:
    """텔레그램 봇 알림"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token and chat_id)
        self._queue = queue.Queue()
        self._stop = False
        
        if self.enabled:
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()
    
    def _worker(self):
        while not self._stop:
            try:
                text = self._queue.get(timeout=1)
                if text is None:
                    break
                
                if requests:
                    url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                    requests.post(url, data={
                        'chat_id': self.chat_id,
                        'text': text,
                        'parse_mode': 'Markdown'
                    }, timeout=5)
            except queue.Empty:
                continue
            except Exception as e:
                logging.warning(f"텔레그램 전송 실패: {e}")
    
    def send(self, message: str):
        if self.enabled:
            self._queue.put(message)
    
    def stop(self):
        self._stop = True
        self._queue.put(None)


class EmailNotifier:
    """이메일 알림"""
    
    def __init__(self, smtp_server: str, smtp_port: int, 
                 username: str, password: str, to_emails: List[str]):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.to_emails = to_emails
        self.enabled = bool(smtp_server and username and password and to_emails)
    
    def send(self, subject: str, body: str, html: bool = False) -> bool:
        if not self.enabled:
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.username
            msg['To'] = ', '.join(self.to_emails)
            
            content_type = 'html' if html else 'plain'
            msg.attach(MIMEText(body, content_type, 'utf-8'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            logging.warning(f"이메일 전송 실패: {e}")
            return False


class UpbitNotificationManager:
    """통합 알림 관리자"""
    
    def __init__(self):
        self.discord: Optional[DiscordNotifier] = None
        self.telegram: Optional[TelegramNotifier] = None
        self.email: Optional[EmailNotifier] = None
        self.event_filters: Dict[str, List[EventType]] = {}
    
    def configure_discord(self, webhook_url: str, 
                         events: List[EventType] = None):
        """Discord 설정"""
        self.discord = DiscordNotifier(webhook_url)
        if events:
            self.event_filters['discord'] = events
    
    def configure_telegram(self, bot_token: str, chat_id: str,
                          events: List[EventType] = None):
        """텔레그램 설정"""
        self.telegram = TelegramNotifier(bot_token, chat_id)
        if events:
            self.event_filters['telegram'] = events
    
    def configure_email(self, smtp_server: str, smtp_port: int,
                       username: str, password: str, to_emails: List[str],
                       events: List[EventType] = None):
        """이메일 설정"""
        self.email = EmailNotifier(smtp_server, smtp_port, 
                                   username, password, to_emails)
        if events:
            self.event_filters['email'] = events
    
    def _should_notify(self, channel: str, event_type: EventType) -> bool:
        if channel not in self.event_filters:
            return True
        return event_type in self.event_filters[channel]
    
    def notify(self, event_type: EventType, message: str, **kwargs):
        """모든 채널로 알림 전송"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        
        # Discord
        if self.discord and self._should_notify('discord', event_type):
            if 'ticker' in kwargs and 'price' in kwargs:
                self.discord.send_trade_alert(
                    event_type, kwargs['ticker'], 
                    kwargs['price'], kwargs.get('pnl', 0)
                )
            else:
                self.discord.send(full_message)
        
        # 텔레그램
        if self.telegram and self._should_notify('telegram', event_type):
            self.telegram.send(full_message)
        
        # 이메일 (중요 이벤트만)
        if self.email and self._should_notify('email', event_type):
            if event_type in [EventType.EMERGENCY, EventType.ERROR]:
                self.email.send(
                    f"[Upbit Trader] {event_type.value.upper()}",
                    full_message
                )
    
    def notify_buy(self, ticker: str, price: float, quantity: float):
        """매수 알림"""
        msg = f"🟢 매수: {ticker}\n가격: ₩{price:,.0f}\n수량: {quantity:.8f}"
        self.notify(EventType.BUY, msg, ticker=ticker, price=price)
    
    def notify_sell(self, ticker: str, price: float, quantity: float, 
                   pnl: float, reason: str = ""):
        """매도 알림"""
        msg = f"🔴 매도: {ticker}\n가격: ₩{price:,.0f}\n손익: {pnl:+.2f}%"
        if reason:
            msg += f"\n사유: {reason}"
        self.notify(EventType.SELL, msg, ticker=ticker, price=price, pnl=pnl)
    
    def notify_error(self, message: str):
        """에러 알림"""
        self.notify(EventType.ERROR, f"❌ 오류: {message}")
    
    def notify_emergency(self, message: str):
        """긴급 알림"""
        self.notify(EventType.EMERGENCY, f"🚨 긴급: {message}")
    
    def stop(self):
        """알림 시스템 종료"""
        if self.telegram:
            self.telegram.stop()
