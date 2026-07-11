from src.leverage_config import DEFAULT_LEVERAGE_CONFIG
from src.paper_position import PaperPosition
from src.portfolio_risk import PortfolioRiskEngine


class PaperPortfolio:

    def __init__(self, config=DEFAULT_LEVERAGE_CONFIG):
        self.positions: list[PaperPosition] = []
        self.config = config
        self.portfolio_risk_engine = PortfolioRiskEngine(config)

    def add_position(self, position: PaperPosition):
        if self.find_open_position(position.symbol) is not None:
            raise ValueError(
                f"Open position already exists for {position.symbol}"
            )

        self.positions.append(position)

    def get_open_positions(self):
        return [
            position
            for position in self.positions
            if position.is_open()
        ]

    def get_closed_positions(self):
        return [
            position
            for position in self.positions
            if not position.is_open()
        ]

    def find_open_position(self, symbol):
        normalized_symbol = symbol.upper()

        for position in self.get_open_positions():
            if position.symbol == normalized_symbol:
                return position

        return None

    def update_market_price(self, symbol, price):
        position = self.find_open_position(symbol)

        if position is None:
            return None

        position.update_price(price)
        return position

    def close_position(
        self,
        symbol,
        price,
        reason="MANUAL",
    ):
        position = self.find_open_position(symbol)

        if position is None:
            return None

        position.close(
            exit_price=price,
            reason=reason,
        )

        return position

    def total_unrealized_pnl(self):
        return round(
            sum(
                position.unrealized_pnl
                for position in self.get_open_positions()
            ),
            8,
        )

    def total_realized_pnl(self):
        return round(
            sum(
                position.realized_pnl
                for position in self.get_closed_positions()
            ),
            8,
        )

    def total_margin_used(self):
        return round(
            sum(
                position.required_margin
                for position in self.get_open_positions()
            ),
            8,
        )

    def total_open_risk(self):
        return round(
            sum(
                position.risk_amount
                for position in self.get_open_positions()
            ),
            8,
        )

    def total_notional_value(self):
        return round(
            sum(
                position.notional_value
                for position in self.get_open_positions()
            ),
            8,
        )

    def equity(self):
        return round(
            self.config.initial_capital
            + self.total_realized_pnl()
            + self.total_unrealized_pnl(),
            8,
        )

    def free_margin(self):
        return round(
            max(
                self.equity()
                - self.total_margin_used(),
                0.0,
            ),
            8,
        )

    def margin_usage_pct(self):
        equity = self.equity()

        if equity <= 0:
            return 1.0

        return round(
            self.total_margin_used() / equity,
            8,
        )

    def open_risk_pct(self):
        equity = self.equity()

        if equity <= 0:
            return 1.0

        return round(
            self.total_open_risk() / equity,
            8,
        )

    def win_rate(self):
        closed_positions = self.get_closed_positions()

        if not closed_positions:
            return 0.0

        wins = sum(
            1
            for position in closed_positions
            if position.realized_pnl > 0
        )

        return round(
            wins / len(closed_positions) * 100,
            2,
        )

    def evaluate_new_position(
        self,
        required_margin,
        risk_amount,
    ):
        return self.portfolio_risk_engine.evaluate_new_position(
            portfolio=self,
            required_margin=required_margin,
            risk_amount=risk_amount,
        )

    def risk_snapshot(self):
        return self.portfolio_risk_engine.summary(self)

    def summary(self):
        return {
            "initial_capital":
                self.config.initial_capital,
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
            "total_notional_value":
                self.total_notional_value(),
            "margin_used":
                self.total_margin_used(),
            "free_margin":
                self.free_margin(),
            "margin_usage_pct":
                self.margin_usage_pct(),
            "open_risk":
                self.total_open_risk(),
            "open_risk_pct":
                self.open_risk_pct(),
            "max_margin_usage_pct":
                self.config.max_margin_usage_pct,
            "max_combined_open_risk_pct":
                self.config.max_combined_open_risk_pct,
            "win_rate":
                self.win_rate(),
        }