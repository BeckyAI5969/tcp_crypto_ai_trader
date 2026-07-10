from datetime import datetime

from src.paper_order import PaperOrder
from src.paper_position import PaperPosition


class PaperExecutionEngine:

    def __init__(self):
        self.order_counter = 0

    def create_order(
        self,
        symbol,
        signal,
        price,
        quantity,
        score,
    ):

        side = "BUY" if signal == "BUY" else "SELL"

        self.order_counter += 1

        order = PaperOrder(
            order_id=f"PAPER-{self.order_counter:08d}",
            symbol=symbol,
            side=side,
            signal=signal,
            price=price,
            quantity=quantity,
            strategy_score=score,
            created_time=datetime.now(),
        )

        return order

    def execute(self, order: PaperOrder):

        order.fill(
            order.price,
            datetime.now(),
        )

        position = PaperPosition(
            symbol=order.symbol,
            side=order.side,
            entry_price=order.filled_price,
            quantity=order.quantity,
            entry_time=order.filled_time,
            strategy_score=order.strategy_score,
            signal=order.signal,
        )

        return position

    def close_position(
        self,
        position: PaperPosition,
        exit_price: float,
    ):

        position.close(
            exit_price,
            datetime.now(),
        )

        return position