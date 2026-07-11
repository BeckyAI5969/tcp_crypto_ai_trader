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
    trailing_stop: float | None = None

    strategy_score: float = 0.0
    signal: str = ""
    exit_reason: str = ""

    leverage: int = 1
    margin_mode: str = "ISOLATED"

    notional_value: float = 0.0
    required_margin: float = 0.0
    risk_amount: float = 0.0

    entry_fee: float = 0.0
    exit_fee: float = 0.0
    funding_fee: float = 0.0

    def __post_init__(self):
        self.symbol = self.symbol.upper()
        self.side = self.side.upper()
        self.margin_mode = self.margin_mode.upper()

        if self.side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")

        if self.entry_price <= 0:
            raise ValueError("entry_price must be greater than zero")

        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero")

        if self.leverage <= 0:
            raise ValueError("leverage must be greater than zero")

        if self.margin_mode != "ISOLATED":
            raise ValueError("Only ISOLATED margin mode is allowed")

        if self.notional_value <= 0:
            self.notional_value = (
                self.entry_price * self.quantity
            )

        if self.required_margin <= 0:
            self.required_margin = (
                self.notional_value / self.leverage
            )

        self.notional_value = round(self.notional_value, 8)
        self.required_margin = round(self.required_margin, 8)
        self.risk_amount = round(max(self.risk_amount, 0.0), 8)

    def update_price(self, price: float):
        if price <= 0:
            raise ValueError("price must be greater than zero")

        gross_pnl = self._gross_pnl(price)

        self.unrealized_pnl = round(
            gross_pnl - self.entry_fee - self.funding_fee,
            8,
        )

    def should_close(self, price: float):
        if self.side == "BUY":
            if (
                self.stop_loss is not None
                and price <= self.stop_loss
            ):
                return True, "STOP_LOSS"

            if (
                self.take_profit is not None
                and price >= self.take_profit
            ):
                return True, "TAKE_PROFIT"

        else:
            if (
                self.stop_loss is not None
                and price >= self.stop_loss
            ):
                return True, "STOP_LOSS"

            if (
                self.take_profit is not None
                and price <= self.take_profit
            ):
                return True, "TAKE_PROFIT"

        return False, ""

    def close(self, exit_price: float, reason: str = ""):
        if not self.is_open():
            return

        if exit_price <= 0:
            raise ValueError(
                "exit_price must be greater than zero"
            )

        self.exit_price = exit_price
        self.exit_time = datetime.now()
        self.exit_reason = reason

        gross_pnl = self._gross_pnl(exit_price)

        self.realized_pnl = round(
            gross_pnl
            - self.entry_fee
            - self.exit_fee
            - self.funding_fee,
            8,
        )

        self.unrealized_pnl = 0.0
        self.status = "CLOSED"

    def is_open(self):
        return self.status == "OPEN"

    def holding_seconds(self):
        end_time = (
            self.exit_time
            if self.exit_time
            else datetime.now()
        )

        return round(
            (end_time - self.entry_time).total_seconds(),
            2,
        )

    def stop_distance_pct(self):
        if self.stop_loss is None:
            return 0.0

        return round(
            abs(
                self.entry_price - self.stop_loss
            ) / self.entry_price,
            8,
        )

    def margin_usage_pct(self, equity: float):
        if equity <= 0:
            return 1.0

        return round(
            self.required_margin / equity,
            8,
        )

    def _gross_pnl(self, price: float):
        if self.side == "BUY":
            return (
                price - self.entry_price
            ) * self.quantity

        return (
            self.entry_price - price
        ) * self.quantity

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
            "realized_pnl": round(self.realized_pnl, 8),
            "unrealized_pnl": round(self.unrealized_pnl, 8),
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "trailing_stop": self.trailing_stop,
            "strategy_score": self.strategy_score,
            "signal": self.signal,
            "exit_reason": self.exit_reason,
            "holding_seconds": self.holding_seconds(),
            "leverage": self.leverage,
            "margin_mode": self.margin_mode,
            "notional_value": round(self.notional_value, 8),
            "required_margin": round(self.required_margin, 8),
            "risk_amount": round(self.risk_amount, 8),
            "entry_fee": round(self.entry_fee, 8),
            "exit_fee": round(self.exit_fee, 8),
            "funding_fee": round(self.funding_fee, 8),
            "stop_distance_pct": self.stop_distance_pct(),
        }