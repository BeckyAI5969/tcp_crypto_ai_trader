"""Paper Execution Engine for TCP Crypto AI Trader."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any


@dataclass(frozen=True)
class PaperTrade:
    symbol: str
    side: str
    quantity: float
    entry_price: float
    leverage: int
    stop_loss: float
    take_profit: float
    status: str
    created_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "leverage": self.leverage,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "status": self.status,
            "created_at": self.created_at,
        }


class PaperExecutionEngine:

    def execute(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        leverage: int,
        stop_loss: float,
        take_profit: float,
    ) -> PaperTrade:

        if quantity <= 0:
            raise ValueError("quantity must be greater than zero")

        side = side.upper()

        if side not in ("BUY", "SELL"):
            raise ValueError("side must be BUY or SELL")

        return PaperTrade(
            symbol=symbol.upper(),
            side=side,
            quantity=round(quantity, 8),
            entry_price=round(entry_price, 8),
            leverage=leverage,
            stop_loss=round(stop_loss, 8),
            take_profit=round(take_profit, 8),
            status="OPEN",
            created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )


if __name__ == "__main__":

    engine = PaperExecutionEngine()

    trade = engine.execute(
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.03,
        entry_price=60000,
        leverage=3,
        stop_loss=59400,
        take_profit=61500,
    )

    print(trade.as_dict())