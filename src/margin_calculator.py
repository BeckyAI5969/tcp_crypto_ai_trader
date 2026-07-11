from dataclasses import dataclass

from src.leverage_config import DEFAULT_LEVERAGE_CONFIG
from src.leverage_manager import LeverageManager


@dataclass(frozen=True)
class MarginCalculation:
    symbol: str
    leverage: int
    notional_value: float
    required_margin: float
    available_margin: float
    margin_usage_pct: float
    approved: bool
    reason: str


class MarginCalculator:

    def __init__(self, config=DEFAULT_LEVERAGE_CONFIG):
        self.config = config
        self.leverage_manager = LeverageManager(config)

    def calculate(
        self,
        symbol: str,
        notional_value: float,
        available_equity: float,
    ) -> MarginCalculation:

        if available_equity <= 0:
            return MarginCalculation(
                symbol=symbol.upper(),
                leverage=0,
                notional_value=notional_value,
                required_margin=0.0,
                available_margin=0.0,
                margin_usage_pct=0.0,
                approved=False,
                reason="No available equity",
            )

        leverage = self.leverage_manager.get_leverage(symbol)
        required = self.leverage_manager.margin_required(
            symbol,
            notional_value,
        )

        usage = required / available_equity

        if usage > self.config.max_margin_usage_pct:
            return MarginCalculation(
                symbol=symbol.upper(),
                leverage=leverage,
                notional_value=round(notional_value, 8),
                required_margin=round(required, 8),
                available_margin=round(available_equity, 8),
                margin_usage_pct=round(usage, 6),
                approved=False,
                reason="Margin usage exceeds configured limit",
            )

        return MarginCalculation(
            symbol=symbol.upper(),
            leverage=leverage,
            notional_value=round(notional_value, 8),
            required_margin=round(required, 8),
            available_margin=round(available_equity, 8),
            margin_usage_pct=round(usage, 6),
            approved=True,
            reason="Margin approved",
        )