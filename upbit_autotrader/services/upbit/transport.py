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



class UpbitTransportMixin:
    """HTTP transport + rate-limit responsibility (SRP)."""

    BASE_URL: str
    session: Any
    timeout: float
    access_key: str
    secret_key: str
    rate_limit_state: Any
    _generate_jwt_token: Any

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        rate_group: str = "default",
        auth: bool = True,
    ) -> Any:
        url = f"{self.BASE_URL}{path}"

        # Open API 2026 guidelines: Prevent duplicate headers across session and request
        if "Content-Type" in self.session.headers:
            self.session.headers.pop("Content-Type", None)

        headers: Dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": "UpbitProAlgoTrader/3.3",
        }

        query_str: Optional[str] = None
        cleaned_params: Optional[Dict[str, Any]] = None
        if params:
            cleaned_params = {k: v for k, v in params.items() if v is not None}
            if cleaned_params:
                query_str = urllib.parse.urlencode(cleaned_params, doseq=True)

        body_str: Optional[str] = None
        if json_data:
            cleaned_body = {k: v for k, v in json_data.items() if v is not None}
            if cleaned_body:
                body_str = urllib.parse.urlencode(cleaned_body, doseq=True)

        if auth and self.access_key and self.secret_key:
            hash_target = query_str or body_str
            headers["Authorization"] = self._generate_jwt_token(hash_target)

        self.rate_limit_state.wait_before_call(rate_group)
        self.rate_limit_state.mark_call(rate_group)

        try:
            method_upper = method.upper()
            if method_upper == "GET":
                resp = self.session.get(url, params=cleaned_params, headers=headers, timeout=self.timeout)
            elif method_upper == "POST":
                headers["Content-Type"] = "application/json"
                resp = self.session.post(url, json=json_data, headers=headers, timeout=self.timeout)
            elif method_upper == "DELETE":
                if json_data is not None:
                    headers["Content-Type"] = "application/json"
                resp = self.session.delete(url, params=cleaned_params, json=json_data, headers=headers, timeout=self.timeout)
            else:
                if json_data is not None:
                    headers["Content-Type"] = "application/json"
                resp = self.session.request(method_upper, url, params=cleaned_params, json=json_data, headers=headers, timeout=self.timeout)
        except Exception as exc:
            if is_rate_limit_error(exc):
                self.rate_limit_state.penalize(rate_group, seconds=1.0)
            raise

        self.rate_limit_state.observe_response(rate_group, resp)

        if resp.status_code == 429:
            self.rate_limit_state.penalize(rate_group, seconds=2.0)
            raise RuntimeError(f"Upbit Rate Limit (429) hit on {path}: {resp.text}")

        if not resp.ok:
            try:
                err_body = resp.json()
                err_msg = err_body.get("error", {}).get("message", resp.text)
                err_name = err_body.get("error", {}).get("name", "ApiError")
                raise RuntimeError(f"Upbit API error ({resp.status_code}, {err_name}): {err_msg}")
            except (ValueError, KeyError):
                resp.raise_for_status()

        return resp.json()
