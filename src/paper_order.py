from dataclasses import dataclass
from datetime import datetime


@dataclass
class PaperPosition:

    symbol: str
    side: str
    entry_price: float
    quantity: float
    entry_time: datetime

    exit_price: float | None = None
    exit_time: datetime | None = None

    status: str = "OPEN"

    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    stop_loss: float | None = None
    take_profit: float | None = None

    strategy_score: float = 0.0
    signal: str = ""

    def update_price(self, price: float):

        if self.side == "BUY":

            self.unrealized_pnl = (
                price - self.entry_price
            ) * self.quantity

        else:

            self.unrealized_pnl = (
                self.entry_price - price
            ) * self.quantity

    def close(
        self,
        exit_price: float,
        exit_time: datetime,
    ):

        self.exit_price = exit_price
        self.exit_time = exit_time

        if self.side == "BUY":

            self.realized_pnl = (
                exit_price - self.entry_price
            ) * self.quantity

        else:

            self.realized_pnl = (
                self.entry_price - exit_price
            ) * self.quantity

        self.status = "CLOSED"

    def is_open(self):

        return self.status == "OPEN"

    def to_dict(self):

        return {

            "symbol": self.symbol,

            "side": self.side,

            "entry_price": self.entry_price,

            "entry_time": self.entry_time.isoformat(),

            "exit_price": self.exit_price,

            "exit_time": (
                self.exit_time.isoformat()
                if self.exit_time
                else None
            ),

            "quantity": self.quantity,

            "status": self.status,

            "realized_pnl": round(
                self.realized_pnl,
                4,
            ),

            "unrealized_pnl": round(
                self.unrealized_pnl,
                4,
            ),

            "stop_loss": self.stop_loss,

            "take_profit": self.take_profit,

            "strategy_score": self.strategy_score,

            "signal": self.signal,
        }