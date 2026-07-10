from src.paper_execution import PaperExecutionEngine
from src.paper_portfolio import PaperPortfolio
from src.paper_trade_log import PaperTradeLogger
from src.paper_report import PaperReport


class PaperTrader:

    def __init__(self):

        self.execution = PaperExecutionEngine()

        self.portfolio = PaperPortfolio()

        self.logger = PaperTradeLogger()

        self.report = PaperReport()

        self.default_quantity = 1.0

    def on_signal(
        self,
        symbol,
        signal,
        price,
        score,
    ):

        if signal == "WAIT":
            return None

        order = self.execution.create_order(
            symbol=symbol,
            signal=signal,
            price=price,
            quantity=self.default_quantity,
            score=score,
        )

        position = self.execution.execute(order)

        self.portfolio.add_position(position)

        self.logger.save_trade(position)

        self.report.save(
            self.portfolio,
            self.logger,
        )

        return position

    def update_market_price(
        self,
        symbol,
        price,
    ):

        self.portfolio.update_market_price(
            symbol,
            price,
        )

        self.report.save(
            self.portfolio,
            self.logger,
        )

    def close_position(
        self,
        position,
        exit_price,
    ):

        self.execution.close_position(
            position,
            exit_price,
        )

        self.logger.save_trade(position)

        self.report.save(
            self.portfolio,
            self.logger,
        )

    def summary(self):

        return self.portfolio.summary()