"""Read-only Binance USDⓈ-M Futures Testnet client.

Safety guarantees:
- Testnet endpoint only
- GET requests only
- No order placement, cancellation, or leverage-changing methods
- API credentials are loaded from environment-backed Settings
- API secrets are never printed

This module uses only the Python standard library.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config import SETTINGS, Settings


TESTNET_BASE_URL = "https://testnet.binancefuture.com"


class BinanceTestnetError(RuntimeError):
    """Raised when Binance Testnet returns an error or cannot be reached."""


@dataclass(frozen=True)
class ConnectionReport:
    connected: bool
    base_url: str
    server_time: int | None
    symbol: str
    ticker_price: float | None
    authenticated: bool
    account_readable: bool
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {
            "connected": self.connected,
            "base_url": self.base_url,
            "server_time": self.server_time,
            "symbol": self.symbol,
            "ticker_price": self.ticker_price,
            "authenticated": self.authenticated,
            "account_readable": self.account_readable,
            "reason": self.reason,
        }


class BinanceTestnetClient:
    """Minimal read-only client for Binance USDⓈ-M Futures Testnet."""

    def __init__(
        self,
        settings: Settings = SETTINGS,
        *,
        timeout_seconds: float = 10.0,
        recv_window: int = 5000,
    ) -> None:
        if not settings.binance_testnet:
            raise ValueError(
                "BinanceTestnetClient requires binance_testnet=True."
            )

        if settings.execution_mode == "LIVE":
            raise ValueError(
                "BinanceTestnetClient cannot run in LIVE mode."
            )

        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero.")

        if not 1 <= recv_window <= 60000:
            raise ValueError("recv_window must be between 1 and 60000.")

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

    def ping(self) -> bool:
        self._public_get("/fapi/v1/ping")
        return True

    def server_time(self) -> int:
        payload = self._public_get("/fapi/v1/time")
        return int(payload["serverTime"])

    def ticker_price(self, symbol: str | None = None) -> float:
        selected_symbol = (symbol or self.settings.symbol).upper()
        payload = self._public_get(
            "/fapi/v1/ticker/price",
            {"symbol": selected_symbol},
        )
        return float(payload["price"])

    def account_balances(self) -> list[dict[str, Any]]:
        self._require_credentials()
        payload = self._signed_get("/fapi/v2/balance")
        if not isinstance(payload, list):
            raise BinanceTestnetError(
                "Unexpected response from balance endpoint."
            )
        return payload

    def usdt_balance(self) -> dict[str, Any] | None:
        for balance in self.account_balances():
            if balance.get("asset") == "USDT":
                return balance
        return None

    def positions(
        self,
        symbol: str | None = None,
        *,
        non_zero_only: bool = False,
    ) -> list[dict[str, Any]]:
        self._require_credentials()

        params: dict[str, object] = {}
        if symbol:
            params["symbol"] = symbol.upper()

        payload = self._signed_get(
            "/fapi/v2/positionRisk",
            params,
        )

        if not isinstance(payload, list):
            raise BinanceTestnetError(
                "Unexpected response from position endpoint."
            )

        if non_zero_only:
            payload = [
                position
                for position in payload
                if float(position.get("positionAmt", 0.0)) != 0.0
            ]

        return payload

    def open_orders(
        self,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        self._require_credentials()

        params: dict[str, object] = {}
        if symbol:
            params["symbol"] = symbol.upper()

        payload = self._signed_get(
            "/fapi/v1/openOrders",
            params,
        )

        if not isinstance(payload, list):
            raise BinanceTestnetError(
                "Unexpected response from open-orders endpoint."
            )

        return payload

    def connection_report(self) -> ConnectionReport:
        symbol = self.settings.symbol

        try:
            self.ping()
            server_time = self.server_time()
            ticker_price = self.ticker_price(symbol)
        except BinanceTestnetError as exc:
            return ConnectionReport(
                connected=False,
                base_url=self.base_url,
                server_time=None,
                symbol=symbol,
                ticker_price=None,
                authenticated=self.authenticated,
                account_readable=False,
                reason=str(exc),
            )

        if not self.authenticated:
            return ConnectionReport(
                connected=True,
                base_url=self.base_url,
                server_time=server_time,
                symbol=symbol,
                ticker_price=ticker_price,
                authenticated=False,
                account_readable=False,
                reason=(
                    "Public Testnet connection succeeded. "
                    "API credentials are not loaded."
                ),
            )

        try:
            self.account_balances()
        except BinanceTestnetError as exc:
            return ConnectionReport(
                connected=True,
                base_url=self.base_url,
                server_time=server_time,
                symbol=symbol,
                ticker_price=ticker_price,
                authenticated=True,
                account_readable=False,
                reason=f"Public connection succeeded; account read failed: {exc}",
            )

        return ConnectionReport(
            connected=True,
            base_url=self.base_url,
            server_time=server_time,
            symbol=symbol,
            ticker_price=ticker_price,
            authenticated=True,
            account_readable=True,
            reason="Public and authenticated read-only checks succeeded.",
        )

    def _public_get(
        self,
        path: str,
        params: dict[str, object] | None = None,
    ) -> Any:
        query = urlencode(params or {})
        return self._request(
            path=path,
            query=query,
            authenticated=False,
        )

    def _signed_get(
        self,
        path: str,
        params: dict[str, object] | None = None,
    ) -> Any:
        self._require_credentials()

        signed_params: dict[str, object] = dict(params or {})
        signed_params["recvWindow"] = self.recv_window
        signed_params["timestamp"] = self.server_time()

        query = urlencode(signed_params)
        signature = hmac.new(
            self.settings.binance_api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        signed_query = f"{query}&signature={signature}"

        return self._request(
            path=path,
            query=signed_query,
            authenticated=True,
        )

    def _request(
        self,
        *,
        path: str,
        query: str,
        authenticated: bool,
    ) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"

        headers = {
            "Accept": "application/json",
            "User-Agent": "TCP-Crypto-AI-Trader/1.0",
        }

        if authenticated:
            headers["X-MBX-APIKEY"] = self.settings.binance_api_key

        request = Request(
            url=url,
            headers=headers,
            method="GET",
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            error_text = exc.read().decode(
                "utf-8",
                errors="replace",
            )
            raise BinanceTestnetError(
                self._format_http_error(
                    status=exc.code,
                    body=error_text,
                )
            ) from exc
        except (URLError, TimeoutError) as exc:
            raise BinanceTestnetError(
                f"Unable to reach Binance Testnet: {exc}"
            ) from exc

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BinanceTestnetError(
                "Binance Testnet returned invalid JSON."
            ) from exc

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
        message = payload.get("msg", "Unknown Binance error")
        return f"HTTP {status}, Binance code {code}: {message}"

    def _require_credentials(self) -> None:
        if not self.authenticated:
            raise BinanceTestnetError(
                "BINANCE_API_KEY and BINANCE_API_SECRET are not loaded."
            )


if __name__ == "__main__":
    client = BinanceTestnetClient()

    started = time.perf_counter()
    report = client.connection_report()
    elapsed_ms = (time.perf_counter() - started) * 1000

    print(report.as_dict())
    print({"elapsed_ms": round(elapsed_ms, 2)})