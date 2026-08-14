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


class UpbitRestClient:
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
            if method.upper() == "GET":
                resp = self.session.get(url, params=cleaned_params, headers=headers, timeout=self.timeout)
            elif method.upper() == "POST":
                headers["Content-Type"] = "application/json"
                resp = self.session.post(url, json=json_data, headers=headers, timeout=self.timeout)
            elif method.upper() == "DELETE":
                resp = self.session.delete(url, params=cleaned_params, json=json_data, headers=headers, timeout=self.timeout)
            else:
                resp = self.session.request(method, url, params=cleaned_params, json=json_data, headers=headers, timeout=self.timeout)
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

    # =========================================================================
    # Exchange API (Accounts, Orders, Chance)
    # =========================================================================

    def get_balances(self) -> List[Dict[str, Any]]:
        """GET /v1/accounts - 전체 계좌 잔고 목록 조회."""
        res = self._request("GET", "/v1/accounts", rate_group="exchange")
        return list(res) if isinstance(res, list) else []

    def get_balance(self, currency: str = "KRW") -> Optional[float]:
        """특정 통화의 주문 가능 잔고 float 반환 (pyupbit 호환)."""
        target = str(currency or "KRW").upper().replace("KRW-", "")
        balances = self.get_balances()
        for item in balances:
            if str(item.get("currency", "")).upper() == target:
                try:
                    return float(item.get("balance", 0.0) or 0.0)
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    def get_chance(self, ticker_or_market: str) -> Optional[Dict[str, Any]]:
        """GET /v1/orders/chance?market={market} - 주문 가능 정보 및 수수료 조회."""
        market = str(ticker_or_market or "").strip()
        if not market:
            return None
        return self._request("GET", "/v1/orders/chance", params={"market": market}, rate_group="exchange")

    def create_order(
        self,
        market: str,
        side: str,
        volume: Optional[Union[float, str]] = None,
        price: Optional[Union[float, str]] = None,
        ord_type: str = "limit",
        identifier: Optional[str] = None,
        time_in_force: Optional[str] = None,
        smp_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST /v1/orders - 주문 생성 (업비트 OpenAPI 스펙 준수)."""
        ot = str(ord_type).lower()
        sd = str(side).lower()
        body: Dict[str, Any] = {
            "market": str(market),
            "side": sd,
            "ord_type": ot,
        }

        # ord_type별 파라미터 제약 준수
        if ot == "price":
            # 시장가 매수: price 필수, volume 금지
            if price is not None:
                body["price"] = str(price)
        elif ot == "market":
            # 시장가 매도: volume 필수, price 금지
            if volume is not None:
                body["volume"] = str(volume)
        elif ot == "best":
            # 최유리 지정가: time_in_force 필수 (ioc 또는 fok)
            if price is not None and sd == "bid":
                body["price"] = str(price)
            if volume is not None:
                body["volume"] = str(volume)
            body["time_in_force"] = str(time_in_force or "ioc").lower()
        else:
            # 지정가 (limit)
            if volume is not None:
                body["volume"] = str(volume)
            if price is not None:
                body["price"] = str(price)
            if time_in_force:
                body["time_in_force"] = str(time_in_force).lower()

        if identifier:
            body["identifier"] = str(identifier).strip()
        if smp_type:
            body["smp_type"] = str(smp_type)

        return self._request("POST", "/v1/orders", json_data=body, rate_group="order")

    def buy_market_order(
        self,
        ticker: str,
        price: Union[float, str],
        identifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """시장가 매수 (ord_type='price', price=주문원화총액) - pyupbit 호환."""
        return self.create_order(
            market=ticker,
            side="bid",
            price=price,
            ord_type="price",
            identifier=identifier,
        )

    def sell_market_order(
        self,
        ticker: str,
        volume: Union[float, str],
        identifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """시장가 매도 (ord_type='market', volume=주문수량) - pyupbit 호환."""
        return self.create_order(
            market=ticker,
            side="ask",
            volume=volume,
            ord_type="market",
            identifier=identifier,
        )

    def buy_limit_order(
        self,
        ticker: str,
        price: Union[float, str],
        volume: Union[float, str],
        identifier: Optional[str] = None,
        time_in_force: Optional[str] = None,
    ) -> Dict[str, Any]:
        """지정가 매수."""
        return self.create_order(
            market=ticker,
            side="bid",
            price=price,
            volume=volume,
            ord_type="limit",
            identifier=identifier,
            time_in_force=time_in_force,
        )

    def sell_limit_order(
        self,
        ticker: str,
        price: Union[float, str],
        volume: Union[float, str],
        identifier: Optional[str] = None,
        time_in_force: Optional[str] = None,
    ) -> Dict[str, Any]:
        """지정가 매도."""
        return self.create_order(
            market=ticker,
            side="ask",
            price=price,
            volume=volume,
            ord_type="limit",
            identifier=identifier,
            time_in_force=time_in_force,
        )

    def get_order(self, uuid_or_identifier: str) -> Optional[Dict[str, Any]]:
        """GET /v1/order - 단건 개별 주문 상세 조회 (uuid 또는 identifier 지원)."""
        if not uuid_or_identifier:
            return None
        val = str(uuid_or_identifier).strip()
        params = {"uuid": val} if "-" in val and len(val) == 36 else {"identifier": val}
        return self._request("GET", "/v1/order", params=params, rate_group="exchange")

    def get_orders_by_uuids(
        self,
        uuids: Optional[List[str]] = None,
        identifiers: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/orders/uuids - 복수 주문 일괄 조회 (최대 100개, uuids[] 또는 identifiers[] 사용)."""
        params: Dict[str, Any] = {}
        if uuids:
            params["uuids[]"] = [str(u) for u in uuids if u]
        elif identifiers:
            params["identifiers[]"] = [str(i) for i in identifiers if i]
        if not params:
            return []
        res = self._request("GET", "/v1/orders/uuids", params=params, rate_group="exchange")
        return list(res) if isinstance(res, list) else []

    def cancel_orders_by_uuids(
        self,
        uuids: Optional[List[str]] = None,
        identifiers: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """DELETE /v1/orders/uuids - 복수 주문 일괄 취소 (최대 20개)."""
        params: Dict[str, Any] = {}
        if uuids:
            params["uuids[]"] = [str(u) for u in uuids if u]
        elif identifiers:
            params["identifiers[]"] = [str(i) for i in identifiers if i]
        if not params:
            return []
        res = self._request("DELETE", "/v1/orders/uuids", params=params, rate_group="order")
        return list(res) if isinstance(res, list) else []

    def get_open_orders(
        self,
        market: Optional[str] = None,
        state: str = "wait",
        page: int = 1,
        limit: int = 100,
        order_by: str = "asc",
    ) -> List[Dict[str, Any]]:
        """GET /v1/orders/open - 체결 대기 주문 목록 조회."""
        params: Dict[str, Any] = {
            "state": state,
            "page": page,
            "limit": limit,
            "order_by": order_by,
        }
        if market:
            params["market"] = str(market)
        res = self._request("GET", "/v1/orders/open", params=params, rate_group="exchange")
        return list(res) if isinstance(res, list) else []

    def get_closed_orders(
        self,
        market: Optional[str] = None,
        state: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """GET /v1/orders/closed - 종료 주문(체결/취소) 목록 조회 (최대 7일)."""
        params: Dict[str, Any] = {"limit": limit}
        if market:
            params["market"] = str(market)
        if state:
            params["state"] = str(state)
        if start_time:
            params["start_time"] = str(start_time)
        if end_time:
            params["end_time"] = str(end_time)
        res = self._request("GET", "/v1/orders/closed", params=params, rate_group="exchange")
        return list(res) if isinstance(res, list) else []

    def cancel_order(self, uuid_or_identifier: str) -> Optional[Dict[str, Any]]:
        """DELETE /v1/order - 주문 취소."""
        if not uuid_or_identifier:
            return None
        val = str(uuid_or_identifier).strip()
        params = {"uuid": val} if "-" in val and len(val) == 36 else {"identifier": val}
        return self._request("DELETE", "/v1/order", params=params, rate_group="order")

    # =========================================================================
    # Quotation API (Tickers, Candles, Markets)
    # =========================================================================

    def get_market_all(self, is_details: bool = False) -> List[Dict[str, Any]]:
        """GET /v1/market/all - 전체 종목 목록 조회."""
        params = {"isDetails": "true" if is_details else "false"}
        res = self._request("GET", "/v1/market/all", params=params, rate_group="quotation", auth=False)
        return list(res) if isinstance(res, list) else []

    def get_current_price(
        self,
        ticker_or_tickers: Union[str, List[str]],
    ) -> Union[float, Dict[str, float], None]:
        """GET /v1/ticker - 현재가 조회 (단일 티커 float 또는 멀티 티커 dict 반환)."""
        if not ticker_or_tickers:
            return None

        if isinstance(ticker_or_tickers, list):
            markets = ",".join([str(t).strip() for t in ticker_or_tickers if t])
            is_single = len(ticker_or_tickers) == 1
        else:
            markets = str(ticker_or_tickers).strip()
            is_single = True

        if not markets:
            return None

        res = self._request(
            "GET",
            "/v1/ticker",
            params={"markets": markets},
            rate_group="quotation_ticker",
            auth=False,
        )
        if not isinstance(res, list) or not res:
            return None

        if is_single and len(res) == 1:
            try:
                return float(res[0].get("trade_price", 0.0) or 0.0)
            except (TypeError, ValueError):
                return 0.0

        price_map: Dict[str, float] = {}
        for row in res:
            market = str(row.get("market") or "")
            try:
                price_map[market] = float(row.get("trade_price", 0.0) or 0.0)
            except (TypeError, ValueError):
                price_map[market] = 0.0
        return price_map

    def buy_best_order(
        self,
        ticker: str,
        price: Union[float, str],
        identifier: Optional[str] = None,
        time_in_force: str = "ioc",
    ) -> Dict[str, Any]:
        """최유리 지정가 매수 (ord_type='best', time_in_force 필수)."""
        return self.create_order(
            market=ticker,
            side="bid",
            price=price,
            ord_type="best",
            identifier=identifier,
            time_in_force=time_in_force,
        )

    def sell_best_order(
        self,
        ticker: str,
        volume: Union[float, str],
        identifier: Optional[str] = None,
        time_in_force: str = "ioc",
    ) -> Dict[str, Any]:
        """최유리 지정가 매도 (ord_type='best', time_in_force 필수)."""
        return self.create_order(
            market=ticker,
            side="ask",
            volume=volume,
            ord_type="best",
            identifier=identifier,
            time_in_force=time_in_force,
        )

    def get_orderbook(
        self,
        markets: Union[str, List[str]],
        count: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/orderbook - 호가 정보 조회."""
        if not markets:
            return []
        market_str = ",".join(markets) if isinstance(markets, list) else str(markets).strip()
        params: Dict[str, Any] = {"markets": market_str}
        if count is not None:
            params["count"] = int(count)
        res = self._request("GET", "/v1/orderbook", params=params, rate_group="quotation_orderbook", auth=False)
        return list(res) if isinstance(res, list) else []

    def get_orderbook_instruments(
        self,
        markets: Optional[Union[str, List[str]]] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/orderbook/instruments - 종목별 호가 정책 및 tick_size 조회."""
        params: Dict[str, Any] = {}
        if markets:
            params["markets"] = ",".join(markets) if isinstance(markets, list) else str(markets).strip()
        res = self._request("GET", "/v1/orderbook/instruments", params=params, rate_group="quotation_orderbook", auth=False)
        return list(res) if isinstance(res, list) else []

    def get_candles_minutes(
        self,
        market: str,
        unit: int = 240,
        count: int = 200,
        to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/candles/minutes/{unit} - 분 캔들 조회."""
        valid_units = {1, 3, 5, 10, 15, 30, 60, 240}
        u = unit if unit in valid_units else 240
        params: Dict[str, Any] = {"market": str(market), "count": max(1, min(200, int(count)))}
        if to:
            params["to"] = str(to)
        res = self._request("GET", f"/v1/candles/minutes/{u}", params=params, rate_group="quotation_candle", auth=False)
        return list(res) if isinstance(res, list) else []

    def get_candles_days(
        self,
        market: str,
        count: int = 200,
        to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/candles/days - 일 캔들 조회."""
        params: Dict[str, Any] = {"market": str(market), "count": max(1, min(200, int(count)))}
        if to:
            params["to"] = str(to)
        res = self._request("GET", "/v1/candles/days", params=params, rate_group="quotation_candle", auth=False)
        return list(res) if isinstance(res, list) else []

    def get_candles_weeks(
        self,
        market: str,
        count: int = 200,
        to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/candles/weeks - 주 캔들 조회."""
        params: Dict[str, Any] = {"market": str(market), "count": max(1, min(200, int(count)))}
        if to:
            params["to"] = str(to)
        res = self._request("GET", "/v1/candles/weeks", params=params, rate_group="quotation_candle", auth=False)
        return list(res) if isinstance(res, list) else []

    def get_candles_months(
        self,
        market: str,
        count: int = 200,
        to: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/candles/months - 월 캔들 조회."""
        params: Dict[str, Any] = {"market": str(market), "count": max(1, min(200, int(count)))}
        if to:
            params["to"] = str(to)
        res = self._request("GET", "/v1/candles/months", params=params, rate_group="quotation_candle", auth=False)
        return list(res) if isinstance(res, list) else []

    def get_ohlcv(
        self,
        ticker: str,
        interval: str = "day",
        count: int = 200,
        to: Optional[str] = None,
    ) -> Any:
        """
        Fetch OHLCV historical candle data as a pandas DataFrame.
        Compatible with pyupbit.get_ohlcv output format.
        """
        import pandas as pd

        ticker_str = str(ticker or "").strip()
        if not ticker_str:
            return pd.DataFrame()

        interval_str = str(interval or "day").strip().lower()
        if interval_str.startswith("minute"):
            try:
                unit = int(interval_str.replace("minute", "") or 1)
            except ValueError:
                unit = 1
            raw_candles = self.get_candles_minutes(ticker_str, unit=unit, count=count, to=to)
        elif interval_str in ("week", "weeks"):
            raw_candles = self.get_candles_weeks(ticker_str, count=count, to=to)
        elif interval_str in ("month", "months"):
            raw_candles = self.get_candles_months(ticker_str, count=count, to=to)
        else:
            raw_candles = self.get_candles_days(ticker_str, count=count, to=to)

        if not raw_candles:
            return pd.DataFrame()

        records = []
        for c in reversed(raw_candles):
            if not isinstance(c, dict):
                continue
            dt_str = c.get("candle_date_time_kst") or c.get("candle_date_time_utc")
            records.append({
                "datetime": dt_str,
                "open": float(c.get("opening_price", 0.0) or 0.0),
                "high": float(c.get("high_price", 0.0) or 0.0),
                "low": float(c.get("low_price", 0.0) or 0.0),
                "close": float(c.get("trade_price", 0.0) or 0.0),
                "volume": float(c.get("candle_acc_trade_volume", 0.0) or 0.0),
                "value": float(c.get("candle_acc_trade_price", 0.0) or 0.0),
            })

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
        return df
