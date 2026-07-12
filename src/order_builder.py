"""Order Builder for TCP Crypto AI Trader."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: str
    order_type: str
    quantity: float
    leverage: int
    entry_price: float
    stop_loss: float
    take_profit: float

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__


class OrderBuilder:
    def build(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        leverage: int,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        order_type: str = "MARKET",
    ) -> OrderRequest:

        if quantity <= 0:
            raise ValueError("quantity must be > 0")
        if leverage < 1:
            raise ValueError("leverage must be >= 1")

        side = side.upper()
        if side not in ("BUY", "SELL"):
            raise ValueError("side must be BUY or SELL")

        return OrderRequest(
            symbol=symbol.upper(),
            side=side,
            order_type=order_type.upper(),
            quantity=round(quantity, 8),
            leverage=leverage,
            entry_price=round(entry_price, 8),
            stop_loss=round(stop_loss, 8),
            take_profit=round(take_profit, 8),
        )


if __name__ == "__main__":
    builder = OrderBuilder()
    order = builder.build(
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.03,
        leverage=3,
        entry_price=60000,
        stop_loss=59400,
        take_profit=61500,
    )
    print(order.as_dict())