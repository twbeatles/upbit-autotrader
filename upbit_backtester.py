"""
Upbit Backtester v1.0
백테스팅 엔진 for Upbit Pro Algo-Trader

변동성 돌파 전략 등 다양한 전략의 과거 성과 분석
"""

import pyupbit
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional
from datetime import datetime, timedelta
import json


@dataclass
class Trade:
    """거래 기록"""
    ticker: str
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: float = 0.0
    quantity: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    reason: str = ""


@dataclass
class BacktestResult:
    """백테스트 결과"""
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float = 0.0
    annualized_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)


class UpbitBacktestEngine:
    """Upbit 백테스팅 엔진"""
    
    def __init__(self, initial_capital: float = 10_000_000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions: Dict[str, Trade] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        
    def reset(self):
        """엔진 초기화"""
        self.capital = self.initial_capital
        self.positions.clear()
        self.trades.clear()
        self.equity_curve.clear()
    
    def get_historical_data(self, ticker: str, interval: str = "day", 
                           count: int = 200) -> pd.DataFrame:
        """과거 데이터 조회"""
        try:
            df = pyupbit.get_ohlcv(ticker, interval=interval, count=count)
            if df is not None:
                df = df.reset_index()
                df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            return df
        except Exception as e:
            print(f"데이터 조회 실패: {e}")
            return pd.DataFrame()
    
    def run_backtest(self, ticker: str, strategy_func: Callable,
                     interval: str = "day", count: int = 200,
                     commission: float = 0.0005) -> BacktestResult:
        """
        백테스트 실행
        
        Args:
            ticker: 코인 심볼 (예: KRW-BTC)
            strategy_func: 전략 함수 (df, index) -> 'BUY', 'SELL', 'HOLD'
            interval: 캔들 간격
            count: 데이터 개수
            commission: 수수료율
        
        Returns:
            BacktestResult
        """
        self.reset()
        
        df = self.get_historical_data(ticker, interval, count)
        if df.empty:
            return BacktestResult(
                start_date="", end_date="",
                initial_capital=self.initial_capital,
                final_capital=self.initial_capital
            )
        
        start_date = str(df['datetime'].iloc[0])
        end_date = str(df['datetime'].iloc[-1])
        
        # 시뮬레이션
        for i in range(30, len(df)):  # 충분한 과거 데이터 확보
            signal = strategy_func(df.iloc[:i+1], i)
            current_price = df['close'].iloc[i]
            current_time = df['datetime'].iloc[i]
            
            if signal == 'BUY' and ticker not in self.positions:
                # 매수
                qty = (self.capital * 0.9) / current_price  # 90% 투자
                cost = current_price * qty * (1 + commission)
                
                if cost <= self.capital:
                    self.capital -= cost
                    self.positions[ticker] = Trade(
                        ticker=ticker,
                        entry_time=current_time,
                        entry_price=current_price,
                        quantity=qty
                    )
            
            elif signal == 'SELL' and ticker in self.positions:
                # 매도
                trade = self.positions[ticker]
                revenue = current_price * trade.quantity * (1 - commission)
                self.capital += revenue
                
                trade.exit_time = current_time
                trade.exit_price = current_price
                pnl = revenue - (trade.entry_price * trade.quantity)
                trade.pnl = pnl
                trade.pnl_pct = (current_price / trade.entry_price - 1) * 100
                
                self.trades.append(trade)
                del self.positions[ticker]
            
            # 자산 가치 기록
            portfolio_value = self.capital
            for pos in self.positions.values():
                portfolio_value += pos.quantity * current_price
            self.equity_curve.append(portfolio_value)
        
        # 남은 포지션 청산
        if ticker in self.positions:
            trade = self.positions[ticker]
            final_price = df['close'].iloc[-1]
            revenue = final_price * trade.quantity * (1 - commission)
            self.capital += revenue
            
            trade.exit_time = df['datetime'].iloc[-1]
            trade.exit_price = final_price
            trade.pnl = revenue - (trade.entry_price * trade.quantity)
            trade.pnl_pct = (final_price / trade.entry_price - 1) * 100
            trade.reason = "청산"
            self.trades.append(trade)
        
        return self._calculate_metrics(start_date, end_date)
    
    def _calculate_metrics(self, start_date: str, end_date: str) -> BacktestResult:
        """성과 지표 계산"""
        final_capital = self.capital
        
        # 기본 수익률
        total_return = (final_capital / self.initial_capital - 1) * 100
        
        # 승률
        winning = [t for t in self.trades if t.pnl > 0]
        losing = [t for t in self.trades if t.pnl <= 0]
        
        win_rate = len(winning) / len(self.trades) * 100 if self.trades else 0
        avg_win = np.mean([t.pnl_pct for t in winning]) if winning else 0
        avg_loss = np.mean([t.pnl_pct for t in losing]) if losing else 0
        
        # Profit Factor
        gross_profit = sum(t.pnl for t in winning)
        gross_loss = abs(sum(t.pnl for t in losing))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # 최대 낙폭 (MDD)
        max_drawdown = 0
        if self.equity_curve:
            peak = self.equity_curve[0]
            for value in self.equity_curve:
                if value > peak:
                    peak = value
                dd = (peak - value) / peak * 100
                max_drawdown = max(max_drawdown, dd)
        
        # 샤프 비율 (일간 수익률 기준)
        sharpe_ratio = 0
        sortino_ratio = 0
        if len(self.equity_curve) > 1:
            returns = pd.Series(self.equity_curve).pct_change().dropna()
            if len(returns) > 0 and returns.std() > 0:
                sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)
            
            # 소르티노 비율
            downside = returns[returns < 0]
            if len(downside) > 0 and downside.std() > 0:
                sortino_ratio = (returns.mean() / downside.std()) * np.sqrt(252)
        
        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=round(total_return, 2),
            max_drawdown=round(max_drawdown, 2),
            sharpe_ratio=round(sharpe_ratio, 2),
            sortino_ratio=round(sortino_ratio, 2),
            win_rate=round(win_rate, 2),
            total_trades=len(self.trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            profit_factor=round(profit_factor, 2),
            trades=self.trades,
            equity_curve=self.equity_curve
        )
    
    def generate_report(self, result: BacktestResult, output_path: str = "backtest_report.html"):
        """HTML 백테스트 리포트 생성"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Upbit 백테스트 리포트</title>
    <style>
        body {{ font-family: 'Malgun Gothic', sans-serif; background: #1a1a2e; color: #edf2f4; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #00b4d8; }}
        .card {{ background: #16213e; border-radius: 10px; padding: 20px; margin: 15px 0; }}
        .metric {{ display: inline-block; width: 200px; margin: 10px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #00b4d8; }}
        .metric-label {{ color: #90e0ef; font-size: 12px; }}
        .positive {{ color: #3fb950; }}
        .negative {{ color: #f85149; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #3d5a80; }}
        th {{ background: #0f3460; color: #90e0ef; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Upbit 백테스트 리포트</h1>
        <p>기간: {result.start_date} ~ {result.end_date}</p>
        
        <div class="card">
            <h2>📈 주요 성과 지표</h2>
            <div class="metric">
                <div class="metric-value {'positive' if result.total_return >= 0 else 'negative'}">{result.total_return}%</div>
                <div class="metric-label">총 수익률</div>
            </div>
            <div class="metric">
                <div class="metric-value negative">-{result.max_drawdown}%</div>
                <div class="metric-label">최대 낙폭 (MDD)</div>
            </div>
            <div class="metric">
                <div class="metric-value">{result.sharpe_ratio}</div>
                <div class="metric-label">샤프 비율</div>
            </div>
            <div class="metric">
                <div class="metric-value">{result.win_rate}%</div>
                <div class="metric-label">승률</div>
            </div>
        </div>
        
        <div class="card">
            <h2>💰 자본 변화</h2>
            <div class="metric">
                <div class="metric-value">₩{result.initial_capital:,.0f}</div>
                <div class="metric-label">초기 자본</div>
            </div>
            <div class="metric">
                <div class="metric-value {'positive' if result.final_capital >= result.initial_capital else 'negative'}">₩{result.final_capital:,.0f}</div>
                <div class="metric-label">최종 자본</div>
            </div>
            <div class="metric">
                <div class="metric-value">{result.total_trades}</div>
                <div class="metric-label">총 거래 수</div>
            </div>
            <div class="metric">
                <div class="metric-value">{result.profit_factor}</div>
                <div class="metric-label">Profit Factor</div>
            </div>
        </div>
        
        <div class="card">
            <h2>📋 거래 내역</h2>
            <table>
                <tr>
                    <th>코인</th>
                    <th>진입 시간</th>
                    <th>진입가</th>
                    <th>청산 시간</th>
                    <th>청산가</th>
                    <th>수익률</th>
                </tr>
                {''.join(f'''
                <tr>
                    <td>{t.ticker}</td>
                    <td>{t.entry_time}</td>
                    <td>₩{t.entry_price:,.0f}</td>
                    <td>{t.exit_time}</td>
                    <td>₩{t.exit_price:,.0f}</td>
                    <td class="{'positive' if t.pnl_pct >= 0 else 'negative'}">{t.pnl_pct:.2f}%</td>
                </tr>
                ''' for t in result.trades[-20:])}
            </table>
        </div>
    </div>
</body>
</html>
"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return output_path


# =============================================================================
# 샘플 전략 함수들
# =============================================================================
def volatility_breakout_strategy(df: pd.DataFrame, i: int, k: float = 0.4) -> str:
    """변동성 돌파 전략"""
    if i < 2:
        return 'HOLD'
    
    prev_range = df['high'].iloc[i-1] - df['low'].iloc[i-1]
    target = df['open'].iloc[i] + prev_range * k
    current = df['close'].iloc[i]
    
    if current > target:
        return 'BUY'
    return 'HOLD'


def ma_crossover_strategy(df: pd.DataFrame, i: int, 
                          short: int = 5, long: int = 20) -> str:
    """이동평균 크로스오버 전략"""
    if i < long:
        return 'HOLD'
    
    ma_short = df['close'].iloc[i-short:i+1].mean()
    ma_long = df['close'].iloc[i-long:i+1].mean()
    
    ma_short_prev = df['close'].iloc[i-short-1:i].mean()
    ma_long_prev = df['close'].iloc[i-long-1:i].mean()
    
    # 골든크로스
    if ma_short > ma_long and ma_short_prev <= ma_long_prev:
        return 'BUY'
    # 데드크로스
    elif ma_short < ma_long and ma_short_prev >= ma_long_prev:
        return 'SELL'
    
    return 'HOLD'
