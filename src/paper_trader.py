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

        if signal not in ["BUY", "SELL"]:
            self.update_market_price(symbol, price)
            return None

        current = self.portfolio.find_open_position(symbol)

        if current is not None:
            current.update_price(price)
            self.logger.log_update(current)
            self.report.save(self.portfolio, self.logger)
            return current

        order = self.execution.create_order(
            symbol=symbol,
            signal=signal,
            price=price,
            quantity=self.default_quantity,
            score=score,
        )

        position = self.execution.execute_order(order)

        self.portfolio.add_position(position)

        self.logger.log_open(position)

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

        position = self.portfolio.update_market_price(
            symbol,
            price,
        )

        if position:
            if position.is_open():
                self.logger.log_update(position)
            else:
                self.logger.log_close(position)

        self.report.save(
            self.portfolio,
            self.logger,
        )

        return position

    def close_position(
        self,
        symbol,
        exit_price,
        reason="MANUAL",
    ):

        position = self.portfolio.close_position(
            symbol,
            exit_price,
            reason,
        )

        if position:
            self.logger.log_close(position)

        self.report.save(
            self.portfolio,
            self.logger,
        )

        return position

    def summary(self):
        return self.portfolio.summary()