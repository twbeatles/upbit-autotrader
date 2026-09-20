"""
Native Upbit REST API client with JWT authentication and pocket-based rate limiting.
Follows the official Upbit Open API specifications (2026).
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
import urllib.parse
import uuid
from typing import Any, Dict, List, Optional, Union

import jwt
import requests

from upbit_autotrader.core.config import Config
from upbit_autotrader.services.rate_limit import RateLimitState, is_rate_limit_error

logger = logging.getLogger(__name__)



from .auth import UpbitAuthMixin
from .transport import UpbitTransportMixin
from .account import UpbitAccountMixin
from .orders import UpbitOrdersMixin
from .order_placement import UpbitOrderPlacementMixin
from .order_query import UpbitOrderQueryMixin
from .order_cancel import UpbitOrderCancelMixin
from .market import UpbitMarketMixin


class UpbitRestClient(UpbitAuthMixin, UpbitTransportMixin, UpbitAccountMixin, UpbitOrdersMixin, UpbitMarketMixin):
    """
    Direct REST API client for Upbit with official JWT authentication,
    Remaining-Req header monitoring, and pocket-based rate limiting.
    Compatible with pyupbit.Upbit duck typing interface.
    """

    BASE_URL = "https://api.upbit.com"

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        session: Optional[requests.Session] = None,
        rate_limit_state: Optional[RateLimitState] = None,
        timeout: float = 10.0,
    ):
        self.access_key = str(access_key or "").strip()
        self.secret_key = str(secret_key or "").strip()
        self.session = session or requests.Session()
        self.timeout = float(timeout)

        intervals = dict(getattr(Config, "API_MIN_INTERVAL_BY_GROUP_SEC", {}) or {})
        self.rate_limit_state = rate_limit_state or RateLimitState(min_interval_by_group=intervals)
