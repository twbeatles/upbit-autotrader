"""Lightweight helpers for Upbit rate-limit adaptation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


def parse_remaining_req(value: str | None) -> dict[str, Any]:
    """Parse Upbit Remaining-Req header into a small dict."""
    result: dict[str, Any] = {}
    if not value:
        return result
    for part in str(value).split(";"):
        if "=" not in part:
            continue
        key, raw = part.split("=", 1)
        key = key.strip().lower()
        raw = raw.strip()
        if not key:
            continue
        try:
            result[key] = int(raw)
        except ValueError:
            result[key] = raw
    return result


@dataclass
class RateLimitState:
    """Group-level wait state driven by Remaining-Req headers and penalties."""

    min_interval_by_group: dict[str, float] = field(default_factory=dict)
    low_remaining_threshold: int = 3
    penalty_decay: float = 0.5
    _last_call_ts: dict[str, float] = field(default_factory=dict)
    _penalty_until_ts: dict[str, float] = field(default_factory=dict)
    _adaptive_interval_by_group: dict[str, float] = field(default_factory=dict)

    def wait_before_call(self, group: str, default_interval: float = 0.0) -> None:
        group = str(group or "default")
        interval = float(self._adaptive_interval_by_group.get(group, self.min_interval_by_group.get(group, default_interval)) or 0.0)
        last_ts = float(self._last_call_ts.get(group, 0.0) or 0.0)
        wait_sec = max(0.0, interval - (time.time() - last_ts))
        penalty_wait = max(0.0, float(self._penalty_until_ts.get(group, 0.0) or 0.0) - time.time())
        wait_sec = max(wait_sec, penalty_wait)
        if wait_sec > 0:
            time.sleep(wait_sec)

    def mark_call(self, group: str) -> None:
        self._last_call_ts[str(group or "default")] = time.time()

    def observe_response(self, group: str, response: Any) -> None:
        header = ""
        headers = getattr(response, "headers", None)
        if headers is not None:
            try:
                header = headers.get("Remaining-Req", "") or headers.get("remaining-req", "")
            except Exception:
                header = ""
        parsed = parse_remaining_req(header)
        sec = parsed.get("sec")
        if not isinstance(sec, int):
            return
        group = str(group or parsed.get("group") or "default")
        base = float(self.min_interval_by_group.get(group, 0.0) or 0.0)
        if sec <= self.low_remaining_threshold:
            self._adaptive_interval_by_group[group] = max(base, 0.25)
        else:
            current = float(self._adaptive_interval_by_group.get(group, base) or 0.0)
            self._adaptive_interval_by_group[group] = max(base, current * self.penalty_decay)

    def penalize(self, group: str, seconds: float = 1.0) -> None:
        group = str(group or "default")
        until_ts = time.time() + max(0.0, float(seconds or 0.0))
        self._penalty_until_ts[group] = max(float(self._penalty_until_ts.get(group, 0.0) or 0.0), until_ts)


def is_rate_limit_error(exc: BaseException) -> bool:
    text = str(exc or "").lower()
    return "429" in text or "too many" in text or "rate limit" in text or "remaining-req" in text

