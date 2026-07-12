"""Trade Plan model for TCP Crypto AI Trader."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any


@dataclass(frozen=True)
class TradePlan:
    symbol: str
    side: str
    confidence: float

    entry_price: float
    quantity: float
    leverage: int

    stop_loss: float
    take_profit: float
    risk_reward: float

    risk_amount: float
    risk_pct: float

    status: str = "READY_FOR_PAPER_EXECUTION"
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "confidence": self.confidence,
            "entry_price": self.entry_price,
            "quantity": self.quantity,
            "leverage": self.leverage,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_reward": self.risk_reward,
            "risk_amount": self.risk_amount,
            "risk_pct": self.risk_pct,
            "status": self.status,
            "created_at": self.created_at,
        }


if __name__ == "__main__":
    plan = TradePlan(
        symbol="BTCUSDT",
        side="BUY",
        confidence=91.5,
        entry_price=60000,
        quantity=0.03,
        leverage=3,
        stop_loss=59400,
        take_profit=61500,
        risk_reward=2.5,
        risk_amount=18,
        risk_pct=0.018,
    )
    print(plan.as_dict())