from dataclasses import dataclass

from src.leverage_config import DEFAULT_LEVERAGE_CONFIG
from src.margin_calculator import MarginCalculator
from src.liquidation_guard import LiquidationGuard


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
        self.margin = MarginCalculator(config)
        self.guard = LiquidationGuard(config)

    def calculate(
        self,
        symbol: str,
        entry_price: float,
        stop_price: float,
        available_equity: float,
        strategy_score: float,
    ) -> PositionSizingDecision:

        if entry_price <= 0 or stop_price <= 0:
            return PositionSizingDecision(
                False,0,0,0,0,0,"Invalid price"
            )

        stop_distance_pct = abs(entry_price-stop_price)/entry_price

        risk_pct = (
            self.config.max_risk_per_trade
            if strategy_score >= 90
            else self.config.base_risk_per_trade
        )

        risk_amount = available_equity * risk_pct

        if stop_distance_pct <= 0:
            return PositionSizingDecision(
                False,0,0,0,0,risk_amount,
                "Invalid stop distance"
            )

        notional = risk_amount / stop_distance_pct

        margin = self.margin.calculate(
            symbol=symbol,
            notional_value=notional,
            available_equity=available_equity,
        )

        if not margin.approved:
            return PositionSizingDecision(
                False,0,notional,
                margin.required_margin,
                margin.leverage,
                risk_amount,
                margin.reason,
            )

        guard = self.guard.evaluate(
            symbol=symbol,
            stop_distance_pct=stop_distance_pct,
        )

        if not guard.approved:
            return PositionSizingDecision(
                False,0,notional,
                margin.required_margin,
                margin.leverage,
                risk_amount,
                guard.reason,
            )

        qty = notional / entry_price

        return PositionSizingDecision(
            approved=True,
            quantity=round(qty,8),
            notional_value=round(notional,8),
            required_margin=margin.required_margin,
            leverage=margin.leverage,
            risk_amount=round(risk_amount,8),
            reason="Position approved",
        )