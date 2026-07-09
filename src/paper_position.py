from dataclasses import dataclass
from datetime import datetime


@dataclass
class PaperPosition:

    symbol: str
    side: str
    quantity: float
    entry_price: float

    opened_at: datetime = datetime.utcnow()

    status: str = "OPEN"

    exit_price: float = 0.0
    closed_at: datetime = None
    realized_pnl: float = 0.0

    def unrealized_pnl(self, current_price: float) -> float:

        if self.side == "BUY":
            return (current_price - self.entry_price) * self.quantity

        if self.side == "SELL":
            return (self.entry_price - current_price) * self.quantity

        return 0.0

    def close(self, exit_price: float):

        self.exit_price = exit_price
        self.closed_at = datetime.utcnow()
        self.realized_pnl = self.unrealized_pnl(exit_price)
        self.status = "CLOSED"

        return self.realized_pnl

    def to_dict(self, current_price=None):

        unrealized = 0.0

        if current_price is not None and self.status == "OPEN":
            unrealized = self.unrealized_pnl(current_price)

        return {
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "status": self.status,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": unrealized,
            "opened_at": self.opened_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else "",
        }