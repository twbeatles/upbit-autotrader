"""
백테스팅 엔진 모듈
Upbit Pro Algo-Trader v3.0

과거 데이터 기반 전략 시뮬레이션 및 성과 분석
"""

import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import statistics

try:
    import pyupbit
    import pandas as pd
    PYUPBIT_AVAILABLE = True
except ImportError:
    PYUPBIT_AVAILABLE = False


@dataclass
class Trade:
    """개별 거래 기록"""
    ticker: str
    entry_time: datetime.datetime
    entry_price: float
    exit_time: Optional[datetime.datetime] = None
    exit_price: Optional[float] = None
    quantity: float = 0
    profit: float = 0
    profit_rate: float = 0
    reason: str = ""


@dataclass
class BacktestResult:
    """백테스트 결과"""
    ticker: str
    start_date: str
    end_date: str
    initial_balance: float
    final_balance: float
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0
    total_profit_rate: float = 0
    win_rate: float = 0
    profit_factor: float = 0
    max_drawdown: float = 0
    max_drawdown_rate: float = 0
    sharpe_ratio: float = 0
    avg_profit_rate: float = 0
    avg_holding_period: float = 0
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)


class BacktestEngine:
    """백테스팅 엔진"""
    
    def __init__(self, initial_balance: float = 10_000_000):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.holdings = 0
        self.avg_price = 0
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.current_trade: Optional[Trade] = None
        
        # 전략 파라미터 (기본값)
        self.k_value = 0.4
        self.ts_start = 5.0
        self.ts_stop = 2.0
        self.loss_cut = 3.0
        self.betting_ratio = 10.0
        self.use_ma_filter = True
        self.use_rsi_filter = True
        self.rsi_upper = 70
    
    def set_params(self, params: dict):
        """전략 파라미터 설정"""
        self.k_value = params.get('k_value', 0.4)
        self.ts_start = params.get('ts_start', 5.0)
        self.ts_stop = params.get('ts_stop', 2.0)
        self.loss_cut = params.get('loss_cut', 3.0)
        self.betting_ratio = params.get('betting_ratio', 10.0)
        self.use_ma_filter = params.get('use_ma_filter', True)
        self.use_rsi_filter = params.get('use_rsi_filter', True)
        self.rsi_upper = params.get('rsi_upper', 70)
    
    def run(self, ticker: str, start_date: str, end_date: str, 
            interval: str = "minute60") -> Optional[BacktestResult]:
        """백테스트 실행"""
        if not PYUPBIT_AVAILABLE:
            print("[백테스트] pyupbit 라이브러리가 필요합니다.")
            return None
        
        # 초기화
        self.balance = self.initial_balance
        self.holdings = 0
        self.avg_price = 0
        self.trades = []
        self.equity_curve = [self.initial_balance]
        self.current_trade = None
        
        # 데이터 조회
        df = self._fetch_data(ticker, start_date, end_date, interval)
        if df is None or len(df) < 20:
            print(f"[백테스트] 데이터 부족: {ticker}")
            return None
        
        # RSI 계산
        df['rsi'] = self._calculate_rsi(df, period=14)
        
        # MA5 계산
        df['ma5'] = df['close'].rolling(window=5).mean()
        
        # 변동성 계산 (전일 고가 - 전일 저가)
        df['range'] = df['high'].shift(1) - df['low'].shift(1)
        
        # 목표가 계산 (당일 시가 + 변동폭 * K)
        df['target'] = df['open'] + df['range'] * self.k_value
        
        # 시뮬레이션
        high_since_buy = 0
        max_profit_rate = 0
        
        for i in range(20, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            current_price = row['close']
            target_price = row['target']
            ma5 = row['ma5']
            rsi = row['rsi']
            
            # 현재 포지션 없음 - 매수 조건 확인
            if self.holdings == 0:
                # 1. 목표가 돌파
                if current_price < target_price:
                    continue
                
                # 2. MA5 필터
                if self.use_ma_filter and current_price < ma5:
                    continue
                
                # 3. RSI 필터
                if self.use_rsi_filter and rsi >= self.rsi_upper:
                    continue
                
                # 매수 실행
                bet_amount = self.balance * (self.betting_ratio / 100)
                if bet_amount > 5000:  # 최소 주문 금액
                    self.holdings = bet_amount / current_price
                    self.avg_price = current_price
                    self.balance -= bet_amount
                    high_since_buy = current_price
                    max_profit_rate = 0
                    
                    self.current_trade = Trade(
                        ticker=ticker,
                        entry_time=row.name,
                        entry_price=current_price,
                        quantity=self.holdings
                    )
            
            # 포지션 보유 중 - 매도 조건 확인
            else:
                profit_rate = (current_price - self.avg_price) / self.avg_price * 100
                
                # 최고가 갱신
                if current_price > high_since_buy:
                    high_since_buy = current_price
                    max_profit_rate = profit_rate
                
                sell_reason = ""
                should_sell = False
                
                # 1. 손절
                if profit_rate <= -self.loss_cut:
                    should_sell = True
                    sell_reason = "손절"
                
                # 2. 트레일링 스톱
                elif max_profit_rate >= self.ts_start:
                    drop = (high_since_buy - current_price) / high_since_buy * 100
                    if drop >= self.ts_stop:
                        should_sell = True
                        sell_reason = "TS"
                
                if should_sell:
                    sell_amount = self.holdings * current_price
                    profit = sell_amount - (self.holdings * self.avg_price)
                    
                    self.balance += sell_amount
                    
                    if self.current_trade:
                        self.current_trade.exit_time = row.name
                        self.current_trade.exit_price = current_price
                        self.current_trade.profit = profit
                        self.current_trade.profit_rate = profit_rate
                        self.current_trade.reason = sell_reason
                        self.trades.append(self.current_trade)
                        self.current_trade = None
                    
                    self.holdings = 0
                    self.avg_price = 0
                    high_since_buy = 0
                    max_profit_rate = 0
            
            # 자산 기록
            current_equity = self.balance + (self.holdings * current_price)
            self.equity_curve.append(current_equity)
        
        # 미청산 포지션 정리
        if self.holdings > 0:
            last_price = df.iloc[-1]['close']
            sell_amount = self.holdings * last_price
            self.balance += sell_amount
            
            if self.current_trade:
                profit_rate = (last_price - self.avg_price) / self.avg_price * 100
                self.current_trade.exit_time = df.index[-1]
                self.current_trade.exit_price = last_price
                self.current_trade.profit = sell_amount - (self.holdings * self.avg_price)
                self.current_trade.profit_rate = profit_rate
                self.current_trade.reason = "종료"
                self.trades.append(self.current_trade)
            
            self.holdings = 0
        
        # 결과 계산
        return self._calculate_result(ticker, start_date, end_date)
    
    def _fetch_data(self, ticker: str, start_date: str, end_date: str, 
                   interval: str) -> Optional[pd.DataFrame]:
        """과거 데이터 조회"""
        try:
            # pyupbit의 캔들 데이터 조회
            # interval 변환
            if interval == "minute60":
                df = pyupbit.get_ohlcv(ticker, interval="minute60", count=2000)
            elif interval == "minute240":
                df = pyupbit.get_ohlcv(ticker, interval="minute240", count=500)
            elif interval == "day":
                df = pyupbit.get_ohlcv(ticker, interval="day", count=365)
            else:
                df = pyupbit.get_ohlcv(ticker, interval=interval, count=1000)
            
            if df is None:
                return None
            
            # 날짜 필터링
            start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            
            df = df[(df.index >= start_dt) & (df.index <= end_dt)]
            
            return df
        except Exception as e:
            print(f"[백테스트] 데이터 조회 실패: {e}")
            return None
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """RSI 계산"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_result(self, ticker: str, start_date: str, 
                         end_date: str) -> BacktestResult:
        """결과 계산"""
        result = BacktestResult(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            initial_balance=self.initial_balance,
            final_balance=self.balance,
            trades=self.trades,
            equity_curve=self.equity_curve
        )
        
        if not self.trades:
            return result
        
        # 거래 통계
        result.total_trades = len(self.trades)
        result.winning_trades = sum(1 for t in self.trades if t.profit > 0)
        result.losing_trades = sum(1 for t in self.trades if t.profit <= 0)
        
        result.total_profit = self.balance - self.initial_balance
        result.total_profit_rate = (result.total_profit / self.initial_balance) * 100
        
        # 승률
        if result.total_trades > 0:
            result.win_rate = (result.winning_trades / result.total_trades) * 100
        
        # Profit Factor
        total_wins = sum(t.profit for t in self.trades if t.profit > 0)
        total_losses = abs(sum(t.profit for t in self.trades if t.profit < 0))
        if total_losses > 0:
            result.profit_factor = total_wins / total_losses
        
        # MDD (Maximum Drawdown)
        peak = self.initial_balance
        max_dd = 0
        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100
            if dd > max_dd:
                max_dd = dd
        result.max_drawdown_rate = max_dd
        result.max_drawdown = peak * (max_dd / 100)
        
        # 평균 수익률
        profit_rates = [t.profit_rate for t in self.trades]
        if profit_rates:
            result.avg_profit_rate = statistics.mean(profit_rates)
        
        # 샤프 비율 (단순화)
        if len(profit_rates) > 1:
            std_dev = statistics.stdev(profit_rates)
            if std_dev > 0:
                result.sharpe_ratio = result.avg_profit_rate / std_dev
        
        # 평균 보유 기간
        holding_periods = []
        for t in self.trades:
            if t.entry_time and t.exit_time:
                delta = t.exit_time - t.entry_time
                holding_periods.append(delta.total_seconds() / 3600)  # 시간 단위
        if holding_periods:
            result.avg_holding_period = statistics.mean(holding_periods)
        
        return result
    
    def get_trades_dataframe(self) -> Optional[pd.DataFrame]:
        """거래 내역 DataFrame 반환"""
        if not PYUPBIT_AVAILABLE or not self.trades:
            return None
        
        data = []
        for t in self.trades:
            data.append({
                '종목': t.ticker,
                '진입시간': t.entry_time,
                '진입가': t.entry_price,
                '청산시간': t.exit_time,
                '청산가': t.exit_price,
                '수익': t.profit,
                '수익률(%)': t.profit_rate,
                '사유': t.reason
            })
        
        return pd.DataFrame(data)
