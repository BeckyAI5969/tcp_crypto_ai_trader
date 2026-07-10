from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4


@dataclass
class PaperOrder:

    symbol: str
    side: str
    signal: str
    price: float
    quantity: float
    strategy_score: float
    created_time: datetime

    order_id: str = ""
    status: str = "PENDING"

    filled_price: float | None = None
    filled_time: datetime | None = None

    cancel_time: datetime | None = None
    reason: str = ""

    def __post_init__(self):

        if not self.order_id:
            self.order_id = str(uuid4())[:8]

    def fill(self, price: float):

        self.status = "FILLED"
        self.filled_price = price
        self.filled_time = datetime.now()

    def cancel(self, reason: str = ""):

        self.status = "CANCELLED"
        self.cancel_time = datetime.now()
        self.reason = reason

    def is_pending(self):

        return self.status == "PENDING"

    def is_filled(self):

        return self.status == "FILLED"

    def is_cancelled(self):

        return self.status == "CANCELLED"

    def to_dict(self):

        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "signal": self.signal,
            "price": self.price,
            "quantity": self.quantity,
            "strategy_score": self.strategy_score,
            "status": self.status,
            "created_time": self.created_time.isoformat(),
            "filled_time": (
                self.filled_time.isoformat()
                if self.filled_time
                else None
            ),
            "filled_price": self.filled_price,
            "cancel_time": (
                self.cancel_time.isoformat()
                if self.cancel_time
                else None
            ),
            "reason": self.reason,
        }