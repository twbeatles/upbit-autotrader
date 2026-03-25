from __future__ import annotations

from typing import Any, cast


Config = cast(Any, None)
time = cast(Any, None)


def bind_runtime(**kwargs):
    globals().update(kwargs)


def _get_indicator_cache_ttl(self, interval):
    self._ensure_indicator_cache_state()
    return float(self._indicator_cache_ttl_sec.get(interval, 5))


def _build_snapshot_cache_key(ticker, interval, rsi_period, volume_period, bb_period):
    return (ticker, interval, int(rsi_period), int(volume_period), int(bb_period))


def _prune_indicator_cache(cache, max_items=1024):
    if len(cache) <= int(max_items):
        return
    oldest_key = min(cache, key=lambda k: cache[k].get("ts", 0))
    cache.pop(oldest_key, None)
