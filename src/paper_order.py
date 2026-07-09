from dataclasses import dataclass
from datetime import datetime


@dataclass
class PaperOrder:

    symbol: str
    side: str
    quantity: float
    price: float

    created_at: datetime = datetime.utcnow()

    status: str = "NEW"

    filled_price: float = 0.0

    filled_qty: float = 0.0

    def execute(self):

        self.status = "FILLED"

        self.filled_price = self.price

        self.filled_qty = self.quantity

    @property
    def value(self):

        return self.quantity * self.price

    def to_dict(self):

        return {
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "filled_price": self.filled_price,
            "filled_qty": self.filled_qty,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }