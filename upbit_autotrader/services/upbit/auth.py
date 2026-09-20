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



class UpbitAuthMixin:
    """JWT authentication responsibility (SRP)."""

    access_key: str
    secret_key: str

    def _generate_jwt_token(self, query_string: Optional[str] = None) -> str:
        """Generate Upbit JWT authentication header with SHA512 query hash."""
        payload: Dict[str, Any] = {
            "access_key": self.access_key,
            "nonce": str(uuid.uuid4()),
            "timestamp": int(datetime.datetime.now(tz=datetime.timezone.utc).timestamp() * 1000),
        }
        if query_string:
            decoded_query = urllib.parse.unquote(query_string)
            query_hash = hashlib.sha512(decoded_query.encode("utf-8")).hexdigest()
            payload["query_hash"] = query_hash
            payload["query_hash_alg"] = "SHA512"

        token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return f"Bearer {token}"
