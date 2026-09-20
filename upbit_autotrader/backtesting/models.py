"""
Upbit Backtester v1.0
백테스팅 엔진 for Upbit Pro Algo-Trader

변동성 돌파 전략 등 다양한 전략의 과거 성과 분석
"""

import pyupbit
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional, Any
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
