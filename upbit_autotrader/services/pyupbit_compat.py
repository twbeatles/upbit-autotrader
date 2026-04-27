"""Fallback object for environments without pyupbit installed."""

from __future__ import annotations

from typing import Any


class MissingPyupbit:
    def __getattr__(self, name: str) -> Any:
        def _missing(*_args: Any, **_kwargs: Any) -> Any:
            raise ImportError("pyupbit library is required. Install it with: pip install pyupbit")

        return _missing


pyupbit_fallback = MissingPyupbit()

