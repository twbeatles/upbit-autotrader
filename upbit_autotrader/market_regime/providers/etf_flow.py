"""External and local market regime data providers."""

from __future__ import annotations

import datetime as _dt
import json
import re
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Any, Dict, Optional

import requests

from upbit_autotrader.services.pyupbit_compat import pyupbit_fallback

try:
    import pyupbit
except ImportError:  # pragma: no cover - handled in callers/tests
    pyupbit = pyupbit_fallback

from upbit_autotrader.market_regime.engine import MarketRegimeSnapshot
from upbit_autotrader.services.rate_limit import RateLimitState, is_rate_limit_error
from .base import ProviderResult, _parse_paren_number



class _FarsideTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self._in_row = False
        self._in_cell = False
        self._cell_parts: list[str] = []
        self._current_row: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag == "tr":
            self._in_row = True
            self._current_row = []
        elif self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._cell_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._in_cell and tag in {"td", "th"}:
            value = "".join(self._cell_parts).strip()
            self._current_row.append(re.sub(r"\s+", " ", value))
            self._cell_parts = []
            self._in_cell = False
        elif self._in_row and tag == "tr":
            if self._current_row:
                self.rows.append(self._current_row)
            self._current_row = []
            self._in_row = False


class FarsideEtfFlowProvider:
    URL = "https://farside.co.uk/btc"
    DATE_RE = re.compile(r"^\d{1,2} [A-Za-z]{3} \d{4}$")

    def __init__(self, session: Any = None, timeout: int = 10, days: int = 3):
        self.session = session or requests
        self.timeout = int(timeout)
        self.days = max(1, int(days))

    @staticmethod
    def _total_to_score(total_flow_musd: float) -> float:
        if total_flow_musd > 0:
            return 70.0
        if total_flow_musd < 0:
            return 30.0
        return 50.0

    def fetch(self) -> ProviderResult:
        try:
            response = self.session.get(self.URL, timeout=self.timeout)
            response.raise_for_status()
            parser = _FarsideTableParser()
            parser.feed(response.text)
        except Exception as exc:
            return ProviderResult(None, "error", details={"reason": str(exc)})

        dated_rows: list[tuple[_dt.datetime, float]] = []
        for row in parser.rows:
            if not row or not self.DATE_RE.match(str(row[0] or "").strip()):
                continue
            total_value = None
            for cell in reversed(row[1:]):
                total_value = _parse_paren_number(cell)
                if total_value is not None:
                    break
            if total_value is None:
                continue
            try:
                parsed_date = _dt.datetime.strptime(str(row[0]), "%d %b %Y")
            except ValueError:
                continue
            dated_rows.append((parsed_date, float(total_value)))

        if not dated_rows:
            return ProviderResult(None, "error", details={"reason": "missing_farside_rows"})

        dated_rows.sort(key=lambda item: item[0])
        recent = dated_rows[-self.days :]
        total_flow = sum(value for _, value in recent)
        return ProviderResult(
            self._total_to_score(total_flow),
            "ok",
            raw_value=total_flow,
            details={"days": len(recent), "total_flow_musd": total_flow},
        )
