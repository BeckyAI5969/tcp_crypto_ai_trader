from datetime import datetime

from src.paper_order import PaperOrder
from src.paper_position import PaperPosition


class PaperExecutionEngine:

    def __init__(self):
        self.order_counter = 0

    def create_order(
        self,
        symbol: str,
        signal: str,
        price: float,
        quantity: float,
        score: float,
    ) -> PaperOrder:

        side = "BUY" if signal == "BUY" else "SELL"
        self.order_counter += 1

        return PaperOrder(
            symbol=symbol,
            side=side,
            signal=signal,
            price=price,
            quantity=quantity,
            strategy_score=score,
            created_time=datetime.now(),
        )

    def execute_order(
        self,
        order: PaperOrder,
        stop_loss_pct: float = 0.01,
        take_profit_pct: float = 0.02,
    ) -> PaperPosition:

        order.fill(order.price)

        position = PaperPosition(
            symbol=order.symbol,
            side=order.side,
            entry_price=order.filled_price,
            quantity=order.quantity,
            entry_time=order.filled_time,
            strategy_score=order.strategy_score,
            signal=order.signal,
        )

        if position.side == "BUY":
            position.stop_loss = round(
                position.entry_price * (1 - stop_loss_pct),
                8,
            )
            position.take_profit = round(
                position.entry_price * (1 + take_profit_pct),
                8,
            )

        else:
            position.stop_loss = round(
                position.entry_price * (1 + stop_loss_pct),
                8,
            )
            position.take_profit = round(
                position.entry_price * (1 - take_profit_pct),
                8,
            )

        return position

    def close_position(
        self,
        position: PaperPosition,
        exit_price: float,
        reason: str = "",
    ) -> PaperPosition:

        position.close(exit_price, reason)

        return position