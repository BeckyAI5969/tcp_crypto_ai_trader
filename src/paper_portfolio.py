from src.paper_position import PaperPosition


class PaperPortfolio:

    def __init__(self):
        self.positions = []

    def add_position(self, position: PaperPosition):
        self.positions.append(position)

    def get_open_positions(self):
        return [p for p in self.positions if p.is_open()]

    def get_closed_positions(self):
        return [p for p in self.positions if not p.is_open()]

    def find_open_position(self, symbol):

        for p in self.get_open_positions():

            if p.symbol == symbol:
                return p

        return None

    def update_market_price(
        self,
        symbol,
        price,
    ):

        position = self.find_open_position(symbol)

        if not position:
            return None

        position.update_price(price)

        should_close, reason = position.should_close(price)

        if should_close:
            position.close(price, reason)

        return position

    def close_position(
        self,
        symbol,
        price,
        reason="MANUAL",
    ):

        position = self.find_open_position(symbol)

        if not position:
            return None

        position.close(price, reason)

        return position

    def total_unrealized_pnl(self):

        return round(
            sum(
                p.unrealized_pnl
                for p in self.get_open_positions()
            ),
            4,
        )

    def total_realized_pnl(self):

        return round(
            sum(
                p.realized_pnl
                for p in self.get_closed_positions()
            ),
            4,
        )

    def equity(self):

        return round(
            self.total_realized_pnl()
            + self.total_unrealized_pnl(),
            4,
        )

    def win_rate(self):

        closed = self.get_closed_positions()

        if not closed:
            return 0.0

        wins = len(
            [
                p
                for p in closed
                if p.realized_pnl > 0
            ]
        )

        return round(
            wins / len(closed) * 100,
            2,
        )

    def summary(self):

        return {

            "open_positions":
                len(self.get_open_positions()),

            "closed_positions":
                len(self.get_closed_positions()),

            "realized_pnl":
                self.total_realized_pnl(),

            "unrealized_pnl":
                self.total_unrealized_pnl(),

            "equity":
                self.equity(),

            "win_rate":
                self.win_rate(),

        }