import pandas as pd


class PortfolioTradeExecutor:

    def __init__(self, engine):
        self.engine = engine
        self.weights = engine.weights()

    def execute_from_coin_report(self, coin_report_path):
        df = pd.read_csv(coin_report_path)

        for _, row in df.iterrows():
            symbol = row["symbol"]
            weight = self.weights.get(symbol, 0)

            if weight <= 0:
                continue

            capital = self.engine.config.initial_capital * weight
            profit = float(row["net_profit"])

            self.engine.capital.release(
                amount=0,
                pnl=profit
            )

            self.engine.add_trade(
                symbol=symbol,
                profit=profit,
                capital=capital,
                entry_time=str(row.get("time", "")),
                exit_time=str(row.get("time", "")),
            )

            self.engine.record_equity()

        return self.engine.trade_dataframe(), self.engine.equity_dataframe()