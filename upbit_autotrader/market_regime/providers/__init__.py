"""Market regime providers subpackage (SOLID SRP split)."""

from upbit_autotrader.services.pyupbit_compat import pyupbit_fallback

try:
    import pyupbit  # noqa: F401  (compat: tests monkeypatch providers.pyupbit)
except ImportError:  # pragma: no cover
    pyupbit = pyupbit_fallback
from .base import ProviderResult, _clamp, _extract_first_numeric, _parse_paren_number, _safe_float
from .breadth import UpbitMarketBreadthProvider
from .btc_trend import BtcTrendVolProvider
from .fear_greed import AlternativeFearGreedProvider
from .global_provider import AlternativeGlobalProvider
from .etf_flow import FarsideEtfFlowProvider, _FarsideTableParser
from .snapshot import build_market_regime_snapshot

__all__ = ["ProviderResult","_safe_float","_clamp","_parse_paren_number","_extract_first_numeric","UpbitMarketBreadthProvider","BtcTrendVolProvider","AlternativeFearGreedProvider","AlternativeGlobalProvider","_FarsideTableParser","FarsideEtfFlowProvider","build_market_regime_snapshot"]
