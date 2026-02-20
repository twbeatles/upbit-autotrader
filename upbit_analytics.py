"""
Upbit Analytics v1.0
트레이딩 통계 및 분석 for Upbit Pro Algo-Trader

일별/월별/코인별 성과 분석 및 리포트 생성
"""

import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict


@dataclass
class DailyPerformance:
    """일별 성과"""
    date: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    max_win: float = 0.0
    max_loss: float = 0.0


@dataclass
class CoinPerformance:
    """코인별 성과"""
    ticker: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    avg_pnl_pct: float = 0.0
    win_rate: float = 0.0


class UpbitTradingAnalytics:
    """Upbit 트레이딩 분석 클래스"""
    
    def __init__(self, history_file: str = "trade_history.json"):
        self.history_file = history_file
        self.trade_history = self._load_history()
    
    def _load_history(self) -> List[Dict]:
        """거래 내역 로드"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def refresh(self):
        """데이터 새로고침"""
        self.trade_history = self._load_history()

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def _extract_trade_dt(trade: Dict) -> Optional[datetime]:
        raw = str(trade.get('timestamp') or trade.get('datetime') or '').strip()
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw)
        except Exception:
            pass
        try:
            return datetime.strptime(raw[:19], '%Y-%m-%d %H:%M:%S')
        except Exception:
            return None
    
    def get_daily_performance(self, days: int = 30) -> List[DailyPerformance]:
        """일별 성과 분석"""
        self.refresh()
        
        daily_data = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'losses': 0,
            'pnl': 0.0, 'max_win': 0.0, 'max_loss': 0.0
        })
        
        cutoff = datetime.now() - timedelta(days=days)
        
        for trade in self.trade_history:
            try:
                trade_dt = self._extract_trade_dt(trade)
                if trade_dt is None:
                    continue
                trade_date = trade_dt.date().isoformat()
                
                if trade_dt < cutoff:
                    continue
                
                profit = self._safe_float(trade.get('profit', 0), 0.0)
                
                daily_data[trade_date]['trades'] += 1
                daily_data[trade_date]['pnl'] += profit
                
                if profit > 0:
                    daily_data[trade_date]['wins'] += 1
                    daily_data[trade_date]['max_win'] = max(
                        daily_data[trade_date]['max_win'], profit
                    )
                elif profit < 0:
                    daily_data[trade_date]['losses'] += 1
                    daily_data[trade_date]['max_loss'] = min(
                        daily_data[trade_date]['max_loss'], profit
                    )
            except:
                continue
        
        result = []
        for date, data in sorted(daily_data.items()):
            result.append(DailyPerformance(
                date=date,
                total_trades=data['trades'],
                winning_trades=data['wins'],
                losing_trades=data['losses'],
                total_pnl=data['pnl'],
                max_win=data['max_win'],
                max_loss=data['max_loss']
            ))
        
        return result
    
    def get_coin_performance(self) -> List[CoinPerformance]:
        """코인별 성과 분석"""
        self.refresh()
        
        coin_data = defaultdict(lambda: {
            'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0.0, 'pnl_list': []
        })
        
        for trade in self.trade_history:
            ticker = trade.get('ticker', 'UNKNOWN')
            profit = trade.get('profit', 0)
            
            coin_data[ticker]['trades'] += 1
            coin_data[ticker]['pnl'] += profit
            coin_data[ticker]['pnl_list'].append(profit)
            
            if profit > 0:
                coin_data[ticker]['wins'] += 1
            elif profit < 0:
                coin_data[ticker]['losses'] += 1
        
        result = []
        for ticker, data in coin_data.items():
            avg_pnl = sum(data['pnl_list']) / len(data['pnl_list']) if data['pnl_list'] else 0
            win_rate = data['wins'] / data['trades'] * 100 if data['trades'] > 0 else 0
            
            result.append(CoinPerformance(
                ticker=ticker,
                total_trades=data['trades'],
                winning_trades=data['wins'],
                losing_trades=data['losses'],
                total_pnl=data['pnl'],
                avg_pnl_pct=round(avg_pnl, 2),
                win_rate=round(win_rate, 2)
            ))
        
        return sorted(result, key=lambda x: x.total_pnl, reverse=True)
    
    def get_monthly_summary(self) -> Dict[str, Dict]:
        """월별 요약"""
        self.refresh()
        
        monthly = defaultdict(lambda: {'trades': 0, 'pnl': 0.0, 'wins': 0})
        
        for trade in self.trade_history:
            try:
                trade_dt = self._extract_trade_dt(trade)
                if trade_dt is None:
                    continue
                month = trade_dt.strftime('%Y-%m')  # YYYY-MM
                profit = self._safe_float(trade.get('profit', 0), 0.0)
                
                monthly[month]['trades'] += 1
                monthly[month]['pnl'] += profit
                if profit > 0:
                    monthly[month]['wins'] += 1
            except:
                continue
        
        return dict(sorted(monthly.items()))
    
    def get_summary_stats(self) -> Dict:
        """전체 요약 통계"""
        self.refresh()
        
        if not self.trade_history:
            return {'total_trades': 0, 'total_pnl': 0, 'win_rate': 0}
        
        total = len(self.trade_history)
        wins = sum(1 for t in self.trade_history if t.get('profit', 0) > 0)
        total_pnl = sum(t.get('profit', 0) for t in self.trade_history)
        
        pnl_list = [t.get('profit', 0) for t in self.trade_history if t.get('profit')]
        
        return {
            'total_trades': total,
            'winning_trades': wins,
            'losing_trades': total - wins,
            'win_rate': round(wins / total * 100, 2) if total > 0 else 0,
            'total_pnl': round(total_pnl, 2),
            'avg_pnl': round(sum(pnl_list) / len(pnl_list), 2) if pnl_list else 0,
            'max_win': max(pnl_list) if pnl_list else 0,
            'max_loss': min(pnl_list) if pnl_list else 0,
        }
    
    def generate_report_html(self, output_path: str = "analytics_report.html") -> str:
        """HTML 분석 리포트 생성"""
        stats = self.get_summary_stats()
        daily = self.get_daily_performance(30)
        coins = self.get_coin_performance()
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Upbit 트레이딩 분석 리포트</title>
    <style>
        body {{ font-family: 'Malgun Gothic', sans-serif; background: #1a1a2e; color: #edf2f4; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #00b4d8; }}
        h2 {{ color: #90e0ef; margin-top: 30px; }}
        .card {{ background: #16213e; border-radius: 10px; padding: 20px; margin: 15px 0; }}
        .stat {{ display: inline-block; width: 180px; margin: 10px; text-align: center; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #00b4d8; }}
        .stat-label {{ color: #90e0ef; font-size: 12px; }}
        .positive {{ color: #3fb950; }}
        .negative {{ color: #f85149; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #3d5a80; }}
        th {{ background: #0f3460; color: #90e0ef; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Upbit 트레이딩 분석 리포트</h1>
        <p>생성일: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="card">
            <h2>📈 전체 요약</h2>
            <div class="stat">
                <div class="stat-value">{stats['total_trades']}</div>
                <div class="stat-label">총 거래</div>
            </div>
            <div class="stat">
                <div class="stat-value">{stats['win_rate']}%</div>
                <div class="stat-label">승률</div>
            </div>
            <div class="stat">
                <div class="stat-value {'positive' if stats['total_pnl'] >= 0 else 'negative'}">{stats['total_pnl']:+.2f}%</div>
                <div class="stat-label">총 손익</div>
            </div>
            <div class="stat">
                <div class="stat-value">{stats['avg_pnl']:+.2f}%</div>
                <div class="stat-label">평균 손익</div>
            </div>
        </div>
        
        <div class="card">
            <h2>🪙 코인별 성과</h2>
            <table>
                <tr><th>코인</th><th>거래수</th><th>승률</th><th>총 손익</th></tr>
                {''.join(f"<tr><td>{c.ticker}</td><td>{c.total_trades}</td><td>{c.win_rate}%</td><td class='{'positive' if c.total_pnl >= 0 else 'negative'}'>{c.total_pnl:+.2f}%</td></tr>" for c in coins[:10])}
            </table>
        </div>
        
        <div class="card">
            <h2>📅 최근 30일 일별 성과</h2>
            <table>
                <tr><th>날짜</th><th>거래수</th><th>승/패</th><th>손익</th></tr>
                {''.join(f"<tr><td>{d.date}</td><td>{d.total_trades}</td><td>{d.winning_trades}/{d.losing_trades}</td><td class='{'positive' if d.total_pnl >= 0 else 'negative'}'>{d.total_pnl:+.2f}%</td></tr>" for d in daily[-15:])}
            </table>
        </div>
    </div>
</body>
</html>
"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return output_path
