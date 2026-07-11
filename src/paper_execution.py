from datetime import datetime

from src.leverage_config import DEFAULT_LEVERAGE_CONFIG
from src.paper_order import PaperOrder
from src.paper_position import PaperPosition


class PaperExecutionEngine:

    def __init__(self, config=DEFAULT_LEVERAGE_CONFIG):
        self.config = config
        self.order_counter = 0

    def create_order(
        self,
        symbol: str,
        signal: str,
        price: float,
        quantity: float,
        score: float,
    ) -> PaperOrder:

        side = "BUY" if signal.upper() == "BUY" else "SELL"
        self.order_counter += 1

        return PaperOrder(
            symbol=symbol.upper(),
            side=side,
            signal=signal.upper(),
            price=float(price),
            quantity=float(quantity),
            strategy_score=float(score),
            created_time=datetime.now(),
        )

    def execute_order(
        self,
        order: PaperOrder,
        stop_loss: float | None = None,
        take_profit: float | None = None,
        leverage: int = 1,
        required_margin: float = 0.0,
        risk_amount: float = 0.0,
        notional_value: float = 0.0,
    ) -> PaperPosition:

        order.fill(order.price)

        leverage = int(leverage)

        if leverage <= 0:
            raise ValueError(
                "leverage must be greater than zero"
            )

        if notional_value <= 0:
            notional_value = (
                float(order.filled_price)
                * float(order.quantity)
            )

        if required_margin <= 0:
            required_margin = (
                notional_value / leverage
            )

        entry_fee = 0.0

        if self.config.include_trading_fee:
            entry_fee = (
                notional_value
                * self.config.taker_fee_rate
            )

        if self.config.include_slippage:
            entry_fee += (
                notional_value
                * self.config.estimated_slippage_rate
            )

        return PaperPosition(
            symbol=order.symbol,
            side=order.side,
            entry_price=float(order.filled_price),
            quantity=float(order.quantity),
            entry_time=order.filled_time,
            strategy_score=float(order.strategy_score),
            signal=order.signal,
            stop_loss=stop_loss,
            take_profit=take_profit,
            leverage=leverage,
            margin_mode=self.config.margin_mode,
            notional_value=round(
                notional_value,
                8,
            ),
            required_margin=round(
                required_margin,
                8,
            ),
            risk_amount=round(
                risk_amount,
                8,
            ),
            entry_fee=round(
                entry_fee,
                8,
            ),
        )

    def close_position(
        self,
        position: PaperPosition,
        exit_price: float,
        reason: str = "",
    ) -> PaperPosition:

        if not position.is_open():
            return position

        exit_notional = (
            float(exit_price)
            * float(position.quantity)
        )

        exit_fee = 0.0

        if self.config.include_trading_fee:
            exit_fee = (
                exit_notional
                * self.config.taker_fee_rate
            )

        if self.config.include_slippage:
            exit_fee += (
                exit_notional
                * self.config.estimated_slippage_rate
            )

        position.exit_fee = round(
            exit_fee,
            8,
        )

        position.close(
            exit_price=float(exit_price),
            reason=reason,
        )

        return position