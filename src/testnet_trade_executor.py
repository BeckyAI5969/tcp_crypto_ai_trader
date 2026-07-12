"""Safe Binance USDⓈ-M Futures Testnet trade executor.

Default behavior:
- Uses Binance Futures Testnet only.
- Validates orders through POST /fapi/v1/order/test.
- Does not submit an order to the matching engine.
- Real-money live trading is not supported.

Submitting an actual Testnet order requires all of the following:
1. TCP_EXECUTION_MODE=TESTNET
2. TCP_BINANCE_TESTNET=true
3. TCP_ENABLE_TESTNET_ORDERS=true
4. Testnet API key and secret loaded from environment variables

This module uses only the Python standard library.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
from os import getenv
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config import SETTINGS, Settings


TESTNET_BASE_URL = "https://testnet.binancefuture.com"
TRUE_VALUES = {"1", "true", "yes", "on"}


class TestnetTradeExecutionError(RuntimeError):
    """Raised when an order cannot be validated or submitted safely."""


@dataclass(frozen=True)
class TestnetOrderRequest:
    symbol: str
    side: str
    quantity: float
    order_type: str = "MARKET"
    position_side: str = "BOTH"
    reduce_only: bool = False
    price: float | None = None
    time_in_force: str | None = None
    client_order_id: str | None = None


@dataclass(frozen=True)
class TestnetExecutionResult:
    success: bool
    mode: str
    submitted_to_matching_engine: bool
    symbol: str
    side: str
    order_type: str
    quantity: float
    order_id: int | None
    client_order_id: str | None
    status: str
    reason: str
    raw_response: dict[str, Any]

    def as_dict(self) -> dict[str, object]:
        return {
            "success": self.success,
            "mode": self.mode,
            "submitted_to_matching_engine":
                self.submitted_to_matching_engine,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "quantity": self.quantity,
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "status": self.status,
            "reason": self.reason,
            "raw_response": self.raw_response,
        }


class TestnetTradeExecutor:
    """Validate or submit Binance Futures Testnet orders."""

    def __init__(
        self,
        settings: Settings = SETTINGS,
        *,
        timeout_seconds: float = 10.0,
        recv_window: int = 5000,
    ) -> None:
        if not settings.binance_testnet:
            raise ValueError(
                "TestnetTradeExecutor requires binance_testnet=True."
            )

        if settings.execution_mode == "LIVE":
            raise ValueError(
                "LIVE execution mode is not supported by this executor."
            )

        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be greater than zero."
            )

        if not 1 <= recv_window <= 60000:
            raise ValueError(
                "recv_window must be between 1 and 60000."
            )

        self.settings = settings
        self.base_url = TESTNET_BASE_URL
        self.timeout_seconds = float(timeout_seconds)
        self.recv_window = int(recv_window)

    @property
    def authenticated(self) -> bool:
        return bool(
            self.settings.binance_api_key
            and self.settings.binance_api_secret
        )

    @property
    def testnet_order_submission_enabled(self) -> bool:
        raw = getenv("TCP_ENABLE_TESTNET_ORDERS", "false")
        return raw.strip().lower() in TRUE_VALUES

    def validate_order(
        self,
        order: TestnetOrderRequest,
    ) -> TestnetExecutionResult:
        """Validate an order without sending it to the matching engine."""

        params = self._build_order_params(order)
        response = self._signed_post(
            "/fapi/v1/order/test",
            params,
        )

        response_dict = (
            response if isinstance(response, dict) else {}
        )

        return TestnetExecutionResult(
            success=True,
            mode="VALIDATE_ONLY",
            submitted_to_matching_engine=False,
            symbol=order.symbol.upper(),
            side=order.side.upper(),
            order_type=order.order_type.upper(),
            quantity=float(order.quantity),
            order_id=self._optional_int(
                response_dict.get("orderId")
            ),
            client_order_id=response_dict.get(
                "clientOrderId"
            ),
            status="VALIDATED",
            reason=(
                "Binance Testnet accepted the order parameters. "
                "The order was not submitted to the matching engine."
            ),
            raw_response=response_dict,
        )

    def submit_testnet_order(
        self,
        order: TestnetOrderRequest,
    ) -> TestnetExecutionResult:
        """Submit an actual order to the Binance Futures Testnet."""

        self._require_testnet_submission_enabled()

        params = self._build_order_params(order)
        params["newOrderRespType"] = "RESULT"

        response = self._signed_post(
            "/fapi/v1/order",
            params,
        )

        if not isinstance(response, dict):
            raise TestnetTradeExecutionError(
                "Unexpected Binance Testnet order response."
            )

        return TestnetExecutionResult(
            success=True,
            mode="TESTNET_ORDER",
            submitted_to_matching_engine=True,
            symbol=str(
                response.get(
                    "symbol",
                    order.symbol.upper(),
                )
            ),
            side=str(
                response.get(
                    "side",
                    order.side.upper(),
                )
            ),
            order_type=str(
                response.get(
                    "type",
                    order.order_type.upper(),
                )
            ),
            quantity=float(
                response.get(
                    "origQty",
                    order.quantity,
                )
            ),
            order_id=self._optional_int(
                response.get("orderId")
            ),
            client_order_id=response.get(
                "clientOrderId"
            ),
            status=str(
                response.get(
                    "status",
                    "UNKNOWN",
                )
            ),
            reason=(
                "Order submitted to Binance Futures Testnet."
            ),
            raw_response=response,
        )

    def execute(
        self,
        order: TestnetOrderRequest,
        *,
        submit: bool = False,
    ) -> TestnetExecutionResult:
        """Validate by default; submit only when explicitly requested."""

        if submit:
            return self.submit_testnet_order(order)

        return self.validate_order(order)

    def _build_order_params(
        self,
        order: TestnetOrderRequest,
    ) -> dict[str, object]:
        symbol = self._validate_symbol(order.symbol)
        side = self._validate_choice(
            "side",
            order.side,
            {"BUY", "SELL"},
        )
        order_type = self._validate_choice(
            "order_type",
            order.order_type,
            {"MARKET", "LIMIT"},
        )
        position_side = self._validate_choice(
            "position_side",
            order.position_side,
            {"BOTH", "LONG", "SHORT"},
        )

        quantity = self._validate_positive(
            "quantity",
            order.quantity,
        )

        params: dict[str, object] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": self._format_decimal(quantity),
            "positionSide": position_side,
            "reduceOnly": (
                "true" if order.reduce_only else "false"
            ),
        }

        if order.client_order_id:
            if len(order.client_order_id) > 36:
                raise ValueError(
                    "client_order_id must not exceed 36 characters."
                )
            params["newClientOrderId"] = order.client_order_id

        if order_type == "LIMIT":
            if order.price is None:
                raise ValueError(
                    "price is required for LIMIT orders."
                )

            price = self._validate_positive(
                "price",
                order.price,
            )

            time_in_force = self._validate_choice(
                "time_in_force",
                order.time_in_force or "GTC",
                {"GTC", "IOC", "FOK", "GTX"},
            )

            params["price"] = self._format_decimal(price)
            params["timeInForce"] = time_in_force

        return params

    def _signed_post(
        self,
        path: str,
        params: dict[str, object],
    ) -> Any:
        self._require_credentials()

        signed_params = dict(params)
        signed_params["recvWindow"] = self.recv_window
        signed_params["timestamp"] = int(
            time.time() * 1000
        )

        query = urlencode(signed_params)

        signature = hmac.new(
            self.settings.binance_api_secret.encode(
                "utf-8"
            ),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        body = f"{query}&signature={signature}".encode(
            "utf-8"
        )

        request = Request(
            url=f"{self.base_url}{path}",
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type":
                    "application/x-www-form-urlencoded",
                "User-Agent":
                    "TCP-Crypto-AI-Trader/1.0",
                "X-MBX-APIKEY":
                    self.settings.binance_api_key,
            },
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            error_body = exc.read().decode(
                "utf-8",
                errors="replace",
            )
            raise TestnetTradeExecutionError(
                self._format_http_error(
                    status=exc.code,
                    body=error_body,
                )
            ) from exc
        except (URLError, TimeoutError) as exc:
            raise TestnetTradeExecutionError(
                f"Unable to reach Binance Testnet: {exc}"
            ) from exc

        if not raw.strip():
            return {}

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TestnetTradeExecutionError(
                "Binance Testnet returned invalid JSON."
            ) from exc

    def _require_credentials(self) -> None:
        if not self.authenticated:
            raise TestnetTradeExecutionError(
                "BINANCE_API_KEY and BINANCE_API_SECRET "
                "are not loaded."
            )

    def _require_testnet_submission_enabled(
        self,
    ) -> None:
        self._require_credentials()

        if self.settings.execution_mode != "TESTNET":
            raise TestnetTradeExecutionError(
                "Actual Testnet order submission requires "
                "TCP_EXECUTION_MODE=TESTNET."
            )

        if not self.testnet_order_submission_enabled:
            raise TestnetTradeExecutionError(
                "Actual Testnet order submission is blocked. "
                "Set TCP_ENABLE_TESTNET_ORDERS=true only "
                "after validation tests pass."
            )

    @staticmethod
    def _validate_symbol(symbol: str) -> str:
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError(
                "symbol must be a non-empty string."
            )
        return symbol.strip().upper()

    @staticmethod
    def _validate_choice(
        name: str,
        value: str,
        choices: set[str],
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                f"{name} must be a string."
            )

        normalized = value.strip().upper()

        if normalized not in choices:
            allowed = ", ".join(sorted(choices))
            raise ValueError(
                f"{name} must be one of: {allowed}."
            )

        return normalized

    @staticmethod
    def _validate_positive(
        name: str,
        value: float,
    ) -> float:
        if not isinstance(value, (int, float)):
            raise TypeError(
                f"{name} must be numeric."
            )

        numeric = float(value)

        if numeric <= 0:
            raise ValueError(
                f"{name} must be greater than zero."
            )

        return numeric

    @staticmethod
    def _format_decimal(value: float) -> str:
        return format(value, ".16f").rstrip("0").rstrip(".")

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _format_http_error(
        *,
        status: int,
        body: str,
    ) -> str:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return f"HTTP {status}: {body[:200]}"

        code = payload.get("code", "unknown")
        message = payload.get(
            "msg",
            "Unknown Binance error",
        )

        return (
            f"HTTP {status}, Binance code "
            f"{code}: {message}"
        )


if __name__ == "__main__":
    executor = TestnetTradeExecutor()

    sample_order = TestnetOrderRequest(
        symbol=SETTINGS.symbol,
        side="BUY",
        quantity=0.001,
        order_type="MARKET",
    )

    if not executor.authenticated:
        print(
            {
                "ready": False,
                "mode": "VALIDATE_ONLY",
                "reason": (
                    "Testnet API credentials are not loaded. "
                    "No request was sent."
                ),
            }
        )
    else:
        result = executor.execute(
            sample_order,
            submit=False,
        )
        print(result.as_dict())