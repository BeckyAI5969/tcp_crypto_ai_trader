from dataclasses import dataclass

from src.leverage_config import DEFAULT_LEVERAGE_CONFIG
from src.liquidation_guard import LiquidationGuard
from src.margin_calculator import MarginCalculator


@dataclass(frozen=True)
class PositionSizingDecision:
    approved: bool
    quantity: float
    notional_value: float
    required_margin: float
    leverage: int
    risk_amount: float
    reason: str


class PositionSizer:

    def __init__(self, config=DEFAULT_LEVERAGE_CONFIG):
        self.config = config
        self.margin_calculator = MarginCalculator(config)
        self.liquidation_guard = LiquidationGuard(config)

    def calculate(
        self,
        symbol: str,
        entry_price: float,
        stop_price: float,
        available_equity: float,
        strategy_score: float,
    ) -> PositionSizingDecision:

        symbol = symbol.upper()

        if entry_price <= 0 or stop_price <= 0:
            return self._reject("Invalid price")

        if available_equity <= 0:
            return self._reject("Available equity must be positive")

        stop_distance = abs(entry_price - stop_price)
        stop_distance_pct = stop_distance / entry_price

        if stop_distance <= 0 or stop_distance_pct <= 0:
            return self._reject("Invalid stop distance")

        risk_pct = (
            self.config.max_risk_per_trade
            if strategy_score >= 90
            else self.config.base_risk_per_trade
        )

        risk_amount = available_equity * risk_pct
        notional_value = risk_amount / stop_distance_pct

        margin = self.margin_calculator.calculate(
            symbol=symbol,
            notional_value=notional_value,
            available_equity=available_equity,
        )

        if not margin.approved:
            return PositionSizingDecision(
                approved=False,
                quantity=0.0,
                notional_value=round(notional_value, 8),
                required_margin=margin.required_margin,
                leverage=margin.leverage,
                risk_amount=round(risk_amount, 8),
                reason=margin.reason,
            )

        liquidation = self.liquidation_guard.evaluate(
            symbol=symbol,
            stop_distance_pct=stop_distance_pct,
        )

        if not liquidation.approved:
            return PositionSizingDecision(
                approved=False,
                quantity=0.0,
                notional_value=round(notional_value, 8),
                required_margin=margin.required_margin,
                leverage=margin.leverage,
                risk_amount=round(risk_amount, 8),
                reason=liquidation.reason,
            )

        quantity = notional_value / entry_price

        return PositionSizingDecision(
            approved=True,
            quantity=round(quantity, 8),
            notional_value=round(notional_value, 8),
            required_margin=round(margin.required_margin, 8),
            leverage=margin.leverage,
            risk_amount=round(risk_amount, 8),
            reason="Position approved",
        )

    @staticmethod
    def _reject(reason: str) -> PositionSizingDecision:
        return PositionSizingDecision(
            approved=False,
            quantity=0.0,
            notional_value=0.0,
            required_margin=0.0,
            leverage=0,
            risk_amount=0.0,
            reason=reason,
        )