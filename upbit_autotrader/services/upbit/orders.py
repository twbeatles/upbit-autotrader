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




from .order_placement import UpbitOrderPlacementMixin
from .order_query import UpbitOrderQueryMixin
from .order_cancel import UpbitOrderCancelMixin


class UpbitOrdersMixin(UpbitOrderPlacementMixin, UpbitOrderQueryMixin, UpbitOrderCancelMixin):
    """Backward-compat composite (SOLID composition)."""
