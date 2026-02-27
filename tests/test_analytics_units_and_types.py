import json
from pathlib import Path
from tempfile import TemporaryDirectory

from upbit_autotrader.analytics.trading_analytics import UpbitTradingAnalytics


def test_analytics_profit_aggregation_handles_mixed_types_safely():
    rows = [
        {"timestamp": "2026-02-24T10:00:00", "ticker": "KRW-BTC", "profit": "1000.5"},
        {"timestamp": "2026-02-24T11:00:00", "ticker": "KRW-ETH", "profit": -250},
        {"timestamp": "2026-02-24T12:00:00", "ticker": "KRW-XRP", "profit": "not-a-number"},
    ]

    with TemporaryDirectory() as td:
        history_path = Path(td) / "history.json"
        history_path.write_text(json.dumps(rows), encoding="utf-8")

        analytics = UpbitTradingAnalytics(str(history_path))
        stats = analytics.get_summary_stats()

    assert abs(float(stats["total_pnl"]) - 750.5) < 1e-9


def test_analytics_html_marks_pnl_as_krw_units():
    rows = [
        {"timestamp": "2026-02-24T10:00:00", "ticker": "KRW-BTC", "profit": 1000},
        {"timestamp": "2026-02-24T11:00:00", "ticker": "KRW-BTC", "profit": -500},
    ]

    with TemporaryDirectory() as td:
        history_path = Path(td) / "history.json"
        report_path = Path(td) / "report.html"
        history_path.write_text(json.dumps(rows), encoding="utf-8")

        analytics = UpbitTradingAnalytics(str(history_path))
        analytics.generate_report_html(str(report_path))

        html = report_path.read_text(encoding="utf-8")

    assert "Total PnL (KRW)" in html
    assert "Average PnL (KRW)" in html
    assert "원" in html
    assert "Total PnL (%)" not in html

