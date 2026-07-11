from dataclasses import dataclass

from src.leverage_config import DEFAULT_LEVERAGE_CONFIG
from src.leverage_manager import LeverageManager


@dataclass(frozen=True)
class LiquidationDecision:
    symbol: str
    leverage: int
    liquidation_buffer_pct: float
    stop_distance_pct: float
    approved: bool
    reason: str


class LiquidationGuard:
    """
    Conservative liquidation safety model for Paper Trading.

    This does NOT calculate Binance's exact liquidation price.
    It enforces a safety buffer so the estimated liquidation
    distance is several times larger than the stop-loss distance.
    """

    def __init__(self, config=DEFAULT_LEVERAGE_CONFIG):
        self.config = config
        self.leverage_manager = LeverageManager(config)

    def evaluate(
        self,
        symbol: str,
        stop_distance_pct: float,
    ) -> LiquidationDecision:

        if stop_distance_pct <= 0:
            return LiquidationDecision(
                symbol=symbol.upper(),
                leverage=0,
                liquidation_buffer_pct=0.0,
                stop_distance_pct=stop_distance_pct,
                approved=False,
                reason="Invalid stop distance",
            )

        leverage = self.leverage_manager.get_leverage(symbol)

        # Conservative approximation:
        estimated_liquidation_distance = 1.0 / leverage

        required_buffer = (
            stop_distance_pct
            * self.config.liquidation_buffer_multiple
        )

        approved = (
            estimated_liquidation_distance >= required_buffer
        )

        return LiquidationDecision(
            symbol=symbol.upper(),
            leverage=leverage,
            liquidation_buffer_pct=round(
                estimated_liquidation_distance, 6
            ),
            stop_distance_pct=round(
                stop_distance_pct, 6
            ),
            approved=approved,
            reason=(
                "Liquidation buffer approved"
                if approved
                else "Liquidation buffer too small"
            ),
        )