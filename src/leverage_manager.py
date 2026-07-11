from dataclasses import dataclass

from src.leverage_config import DEFAULT_LEVERAGE_CONFIG


@dataclass(frozen=True)
class LeverageDecision:
    symbol: str
    leverage: int
    margin_mode: str
    approved: bool
    reason: str


class LeverageManager:

    def __init__(self, config=DEFAULT_LEVERAGE_CONFIG):
        self.config = config

    def evaluate(self, symbol: str) -> LeverageDecision:
        normalized_symbol = symbol.upper()

        try:
            leverage = self.config.get_leverage(normalized_symbol)
        except KeyError as error:
            return LeverageDecision(
                symbol=normalized_symbol,
                leverage=0,
                margin_mode=self.config.margin_mode.upper(),
                approved=False,
                reason=str(error),
            )

        if leverage <= 0:
            return LeverageDecision(
                symbol=normalized_symbol,
                leverage=leverage,
                margin_mode=self.config.margin_mode.upper(),
                approved=False,
                reason="Leverage must be greater than zero",
            )

        if leverage > self.config.max_allowed_leverage:
            return LeverageDecision(
                symbol=normalized_symbol,
                leverage=leverage,
                margin_mode=self.config.margin_mode.upper(),
                approved=False,
                reason="Leverage exceeds configured maximum",
            )

        return LeverageDecision(
            symbol=normalized_symbol,
            leverage=leverage,
            margin_mode=self.config.margin_mode.upper(),
            approved=True,
            reason="Leverage approved",
        )

    def get_leverage(self, symbol: str) -> int:
        decision = self.evaluate(symbol)

        if not decision.approved:
            raise ValueError(decision.reason)

        return decision.leverage

    def margin_required(
        self,
        symbol: str,
        notional_value: float,
    ) -> float:
        if notional_value < 0:
            raise ValueError(
                "notional_value cannot be negative"
            )

        leverage = self.get_leverage(symbol)

        return round(
            notional_value / leverage,
            8,
        )

    def notional_capacity(
        self,
        symbol: str,
        available_margin: float,
    ) -> float:
        if available_margin < 0:
            raise ValueError(
                "available_margin cannot be negative"
            )

        leverage = self.get_leverage(symbol)

        return round(
            available_margin * leverage,
            8,
        )

    def summary(self) -> dict:
        return {
            "margin_mode":
                self.config.margin_mode.upper(),
            "symbol_leverage":
                dict(self.config.symbol_leverage),
            "max_allowed_leverage":
                self.config.max_allowed_leverage,
        }