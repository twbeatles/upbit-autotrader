"""
텔레그램 알림 모듈
Upbit Pro Algo-Trader v3.0

거래 알림, 일일 리포트 등을 텔레그램으로 발송
"""

import asyncio
import threading
from datetime import datetime
from typing import Optional

# 텔레그램 봇 라이브러리 (옵션)
try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


class TelegramNotifier:
    """텔레그램 알림 발송 클래스"""
    
    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.bot: Optional[Bot] = None
        self.enabled = False
        self._loop = None
        self._thread = None
        
        # 알림 설정
        self.notify_buy = True      # 매수 알림
        self.notify_sell = True     # 매도 알림
        self.notify_loss = True     # 손절 알림
        self.notify_daily = True    # 일일 리포트
        
        if bot_token and chat_id:
            self.initialize()
    
    def initialize(self) -> bool:
        """봇 초기화"""
        if not TELEGRAM_AVAILABLE:
            print("[텔레그램] python-telegram-bot 라이브러리가 설치되지 않았습니다.")
            return False
        
        if not self.bot_token or not self.chat_id:
            return False
        
        try:
            self.bot = Bot(token=self.bot_token)
            self.enabled = True
            
            # 비동기 이벤트 루프를 별도 스레드에서 실행
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            
            return True
        except Exception as e:
            print(f"[텔레그램] 초기화 실패: {e}")
            self.enabled = False
            return False
    
    def _run_loop(self):
        """이벤트 루프 실행"""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()
    
    def _schedule_coroutine(self, coro):
        """코루틴을 이벤트 루프에 스케줄"""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, self._loop)
    
    async def _send_message_async(self, message: str) -> bool:
        """비동기 메시지 발송"""
        if not self.bot or not self.enabled:
            return False
        
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            return True
        except TelegramError as e:
            print(f"[텔레그램] 발송 실패: {e}")
            return False
    
    def send_message(self, message: str):
        """동기 래퍼 - 메시지 발송"""
        if not self.enabled:
            return
        self._schedule_coroutine(self._send_message_async(message))
    
    def send_buy_alert(self, ticker: str, price: float, amount: float):
        """매수 체결 알림"""
        if not self.notify_buy:
            return
        
        coin = ticker.replace("KRW-", "")
        message = (
            f"🟢 <b>매수 체결</b>\n\n"
            f"종목: <b>{coin}</b>\n"
            f"가격: {price:,.0f}원\n"
            f"금액: {amount:,.0f}원\n"
            f"시간: {datetime.now().strftime('%H:%M:%S')}"
        )
        self.send_message(message)
    
    def send_sell_alert(self, ticker: str, price: float, profit_rate: float, reason: str = ""):
        """매도 체결 알림"""
        if not self.notify_sell:
            return
        
        coin = ticker.replace("KRW-", "")
        emoji = "🔴" if profit_rate < 0 else "🟢"
        profit_text = f"+{profit_rate:.2f}%" if profit_rate >= 0 else f"{profit_rate:.2f}%"
        
        message = (
            f"{emoji} <b>매도 체결</b>\n\n"
            f"종목: <b>{coin}</b>\n"
            f"가격: {price:,.0f}원\n"
            f"수익률: <b>{profit_text}</b>\n"
            f"사유: {reason}\n"
            f"시간: {datetime.now().strftime('%H:%M:%S')}"
        )
        self.send_message(message)
    
    def send_loss_cut_alert(self, ticker: str, price: float, loss_rate: float):
        """손절 알림"""
        if not self.notify_loss:
            return
        
        coin = ticker.replace("KRW-", "")
        message = (
            f"🛑 <b>손절 매도</b>\n\n"
            f"종목: <b>{coin}</b>\n"
            f"가격: {price:,.0f}원\n"
            f"손실률: <b>{loss_rate:.2f}%</b>\n"
            f"시간: {datetime.now().strftime('%H:%M:%S')}"
        )
        self.send_message(message)
    
    def send_daily_report(self, stats: dict):
        """일일 리포트 발송"""
        if not self.notify_daily:
            return
        
        total_profit = stats.get('total_profit', 0)
        profit_rate = stats.get('profit_rate', 0)
        trade_count = stats.get('trade_count', 0)
        win_rate = stats.get('win_rate', 0)
        
        emoji = "📈" if total_profit >= 0 else "📉"
        profit_text = f"+{total_profit:,.0f}원" if total_profit >= 0 else f"{total_profit:,.0f}원"
        rate_text = f"+{profit_rate:.2f}%" if profit_rate >= 0 else f"{profit_rate:.2f}%"
        
        message = (
            f"{emoji} <b>일일 거래 리포트</b>\n\n"
            f"📊 총 손익: <b>{profit_text}</b> ({rate_text})\n"
            f"🔄 거래 횟수: {trade_count}회\n"
            f"🎯 승률: {win_rate:.1f}%\n\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d')}"
        )
        self.send_message(message)
    
    def send_start_alert(self):
        """자동매매 시작 알림"""
        message = (
            f"🚀 <b>자동매매 시작</b>\n\n"
            f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_message(message)
    
    def send_stop_alert(self):
        """자동매매 중지 알림"""
        message = (
            f"⏹️ <b>자동매매 중지</b>\n\n"
            f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_message(message)
    
    def send_test_message(self) -> bool:
        """테스트 메시지 발송"""
        if not self.enabled:
            return False
        
        message = (
            f"✅ <b>테스트 메시지</b>\n\n"
            f"Upbit Pro Algo-Trader 텔레그램 알림이 정상 작동합니다.\n"
            f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.send_message(message)
        return True
    
    def update_settings(self, bot_token: str, chat_id: str):
        """설정 업데이트"""
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.initialize()
    
    def set_notifications(self, buy: bool, sell: bool, loss: bool, daily: bool):
        """알림 유형 설정"""
        self.notify_buy = buy
        self.notify_sell = sell
        self.notify_loss = loss
        self.notify_daily = daily
    
    def stop(self):
        """종료"""
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.enabled = False


# 싱글톤 인스턴스
_notifier_instance: Optional[TelegramNotifier] = None

def get_telegram_notifier() -> TelegramNotifier:
    """텔레그램 노티파이어 싱글톤 인스턴스 반환"""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = TelegramNotifier()
    return _notifier_instance
