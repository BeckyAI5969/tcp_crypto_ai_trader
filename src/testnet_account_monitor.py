"""Read-only Binance Futures Testnet account monitor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from binance_testnet_client import BinanceTestnetClient, BinanceTestnetError


@dataclass(frozen=True)
class AccountSnapshot:
    ready: bool
    balance: float | None
    available_balance: float | None
    unrealized_pnl: float | None
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__


class TestnetAccountMonitor:

    def __init__(self) -> None:
        self.client = BinanceTestnetClient()

    def snapshot(self) -> AccountSnapshot:
        try:
            usdt = self.client.usdt_balance()
        except BinanceTestnetError as exc:
            return AccountSnapshot(
                ready=False,
                balance=None,
                available_balance=None,
                unrealized_pnl=None,
                reason=str(exc),
            )

        if usdt is None:
            return AccountSnapshot(
                ready=False,
                balance=None,
                available_balance=None,
                unrealized_pnl=None,
                reason="USDT balance not found.",
            )

        return AccountSnapshot(
            ready=True,
            balance=float(usdt.get("balance", 0)),
            available_balance=float(usdt.get("availableBalance", 0)),
            unrealized_pnl=float(usdt.get("crossUnPnl", 0)),
            reason="OK",
        )


if __name__ == "__main__":
    monitor = TestnetAccountMonitor()
    print(monitor.snapshot().as_dict())