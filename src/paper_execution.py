from src.paper_order import PaperOrder
from src.paper_position import PaperPosition


class PaperExecutionEngine:

    def __init__(self):
        self.orders = []
        self.positions = []

    def execute_order(
        self,
        symbol,
        side,
        quantity,
        price,
    ):

        order = PaperOrder(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
        )

        order.execute()

        self.orders.append(order)

        position = PaperPosition(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=price,
        )

        self.positions.append(position)

        return position

    def open_positions(self):

        return [
            p
            for p in self.positions
            if p.status == "OPEN"
        ]

    def close_position(
        self,
        position,
        exit_price,
    ):

        pnl = position.close(exit_price)

        return pnl

    def order_history(self):

        return [
            o.to_dict()
            for o in self.orders
        ]

    def position_history(self):

        return [
            p.to_dict()
            for p in self.positions
        ]