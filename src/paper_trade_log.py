from src.paper_position import PaperPosition


class PaperPortfolio:

    def __init__(self):

        self.positions = []

    def add_position(self, position: PaperPosition):

        self.positions.append(position)

    def get_open_positions(self):

        return [
            p
            for p in self.positions
            if p.is_open()
        ]

    def get_closed_positions(self):

        return [
            p
            for p in self.positions
            if not p.is_open()
        ]

    def update_market_price(
        self,
        symbol,
        price,
    ):

        for p in self.get_open_positions():

            if p.symbol == symbol:

                p.update_price(price)

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

        }