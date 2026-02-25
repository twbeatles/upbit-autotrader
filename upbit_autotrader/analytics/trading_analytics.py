"""
Upbit Trading Analytics helpers.
"""

import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional


@dataclass
class DailyPerformance:
    """Daily performance aggregate."""

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
    """Per-coin performance aggregate."""

    ticker: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    avg_pnl_pct: float = 0.0
    win_rate: float = 0.0


class UpbitTradingAnalytics:
    """Load trade history and build summary analytics."""

    def __init__(self, history_file: str = "trade_history.json"):
        self.history_file = history_file
        self.trade_history = self._load_history()

    def _load_history(self) -> List[Dict]:
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def refresh(self) -> None:
        self.trade_history = self._load_history()

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def _extract_trade_dt(trade: Dict) -> Optional[datetime]:
        raw = str(trade.get("timestamp") or trade.get("datetime") or "").strip()
        if not raw:
            return None

        try:
            return datetime.fromisoformat(raw)
        except Exception:
            pass

        try:
            return datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            return None

    def get_daily_performance(self, days: int = 30) -> List[DailyPerformance]:
        self.refresh()

        cutoff = datetime.now() - timedelta(days=days)
        daily_data = defaultdict(
            lambda: {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "pnl": 0.0,
                "max_win": 0.0,
                "max_loss": 0.0,
            }
        )

        for trade in self.trade_history:
            trade_dt = self._extract_trade_dt(trade)
            if trade_dt is None or trade_dt < cutoff:
                continue

            trade_date = trade_dt.date().isoformat()
            profit = self._safe_float(trade.get("profit", 0), 0.0)

            bucket = daily_data[trade_date]
            bucket["trades"] += 1
            bucket["pnl"] += profit
            if profit > 0:
                bucket["wins"] += 1
                bucket["max_win"] = max(bucket["max_win"], profit)
            elif profit < 0:
                bucket["losses"] += 1
                bucket["max_loss"] = min(bucket["max_loss"], profit)

        result: List[DailyPerformance] = []
        for date, data in sorted(daily_data.items()):
            result.append(
                DailyPerformance(
                    date=date,
                    total_trades=data["trades"],
                    winning_trades=data["wins"],
                    losing_trades=data["losses"],
                    total_pnl=data["pnl"],
                    max_win=data["max_win"],
                    max_loss=data["max_loss"],
                )
            )
        return result

    def get_coin_performance(self) -> List[CoinPerformance]:
        self.refresh()

        coin_data = defaultdict(
            lambda: {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "pnl": 0.0,
                "pnl_list": [],
            }
        )

        for trade in self.trade_history:
            ticker = str(trade.get("ticker") or "UNKNOWN")
            profit = self._safe_float(trade.get("profit", 0), 0.0)

            bucket = coin_data[ticker]
            bucket["trades"] += 1
            bucket["pnl"] += profit
            bucket["pnl_list"].append(profit)
            if profit > 0:
                bucket["wins"] += 1
            elif profit < 0:
                bucket["losses"] += 1

        rows: List[CoinPerformance] = []
        for ticker, data in coin_data.items():
            avg_pnl = sum(data["pnl_list"]) / len(data["pnl_list"]) if data["pnl_list"] else 0.0
            win_rate = data["wins"] / data["trades"] * 100.0 if data["trades"] > 0 else 0.0
            rows.append(
                CoinPerformance(
                    ticker=ticker,
                    total_trades=data["trades"],
                    winning_trades=data["wins"],
                    losing_trades=data["losses"],
                    total_pnl=data["pnl"],
                    avg_pnl_pct=round(avg_pnl, 2),
                    win_rate=round(win_rate, 2),
                )
            )

        return sorted(rows, key=lambda x: x.total_pnl, reverse=True)

    def get_monthly_summary(self) -> Dict[str, Dict]:
        self.refresh()

        monthly = defaultdict(lambda: {"trades": 0, "pnl": 0.0, "wins": 0})
        for trade in self.trade_history:
            trade_dt = self._extract_trade_dt(trade)
            if trade_dt is None:
                continue

            month = trade_dt.strftime("%Y-%m")
            profit = self._safe_float(trade.get("profit", 0), 0.0)
            bucket = monthly[month]
            bucket["trades"] += 1
            bucket["pnl"] += profit
            if profit > 0:
                bucket["wins"] += 1

        return dict(sorted(monthly.items()))

    def get_summary_stats(self) -> Dict:
        self.refresh()
        if not self.trade_history:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_pnl": 0,
                "max_win": 0,
                "max_loss": 0,
            }

        pnl_list = [self._safe_float(t.get("profit", 0), 0.0) for t in self.trade_history]
        total = len(self.trade_history)
        wins = sum(1 for v in pnl_list if v > 0)

        non_zero_pnl = [v for v in pnl_list if v != 0.0]
        total_pnl = sum(pnl_list)

        return {
            "total_trades": total,
            "winning_trades": wins,
            "losing_trades": total - wins,
            "win_rate": round(wins / total * 100, 2) if total > 0 else 0,
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(sum(non_zero_pnl) / len(non_zero_pnl), 2) if non_zero_pnl else 0,
            "max_win": max(non_zero_pnl) if non_zero_pnl else 0,
            "max_loss": min(non_zero_pnl) if non_zero_pnl else 0,
        }

    def generate_report_html(self, output_path: str = "analytics_report.html") -> str:
        """Generate HTML report with KRW unit for PnL metrics."""

        stats = self.get_summary_stats()
        daily = self.get_daily_performance(30)
        coins = self.get_coin_performance()

        coin_rows = "".join(
            (
                f"<tr><td>{c.ticker}</td><td>{c.total_trades}</td><td>{c.win_rate}%</td>"
                f"<td class=\"{'positive' if c.total_pnl >= 0 else 'negative'}\">{c.total_pnl:+,.0f}원</td></tr>"
            )
            for c in coins[:10]
        )
        daily_rows = "".join(
            (
                f"<tr><td>{d.date}</td><td>{d.total_trades}</td>"
                f"<td>{d.winning_trades}/{d.losing_trades}</td>"
                f"<td class=\"{'positive' if d.total_pnl >= 0 else 'negative'}\">{d.total_pnl:+,.0f}원</td></tr>"
            )
            for d in daily[-15:]
        )

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Upbit Trading Analytics Report</title>
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
        <h1>Upbit Trading Analytics Report</h1>
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="card">
            <h2>Summary</h2>
            <div class="stat">
                <div class="stat-value">{stats['total_trades']}</div>
                <div class="stat-label">Total Trades</div>
            </div>
            <div class="stat">
                <div class="stat-value">{stats['win_rate']}%</div>
                <div class="stat-label">Win Rate</div>
            </div>
            <div class="stat">
                <div class="stat-value {'positive' if stats['total_pnl'] >= 0 else 'negative'}">{stats['total_pnl']:+,.0f}원</div>
                <div class="stat-label">Total PnL (KRW)</div>
            </div>
            <div class="stat">
                <div class="stat-value">{stats['avg_pnl']:+,.0f}원</div>
                <div class="stat-label">Average PnL (KRW)</div>
            </div>
        </div>

        <div class="card">
            <h2>Coin Performance</h2>
            <table>
                <tr><th>Ticker</th><th>Trades</th><th>Win Rate</th><th>Total PnL (KRW)</th></tr>
                {coin_rows}
            </table>
        </div>

        <div class="card">
            <h2>Last 30 Days</h2>
            <table>
                <tr><th>Date</th><th>Trades</th><th>W/L</th><th>PnL (KRW)</th></tr>
                {daily_rows}
            </table>
        </div>
    </div>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return output_path
