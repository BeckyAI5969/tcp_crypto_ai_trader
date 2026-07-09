import pandas as pd

from src.portfolio_metrics import PortfolioMetrics


class PortfolioStatistics:

    def __init__(self, trades_df, equity_df):
        self.trades_df = trades_df
        self.equity_df = equity_df

    def calculate(self):
        metrics = PortfolioMetrics.summarize(
            self.trades_df,
            self.equity_df
        )

        metrics["symbols"] = (
            self.trades_df["symbol"].nunique()
            if not self.trades_df.empty and "symbol" in self.trades_df.columns
            else 0
        )

        metrics["best_symbol"] = self.best_symbol()
        metrics["worst_symbol"] = self.worst_symbol()

        return metrics

    def by_symbol(self):
        if self.trades_df.empty:
            return pd.DataFrame()

        rows = []

        for symbol, group in self.trades_df.groupby("symbol"):
            equity = pd.DataFrame({
                "equity": group["profit"].cumsum()
            })

            summary = PortfolioMetrics.summarize(group, equity)
            summary["symbol"] = symbol

            rows.append(summary)

        return pd.DataFrame(rows)

    def best_symbol(self):
        symbol_report = self.by_symbol()

        if symbol_report.empty:
            return ""

        return symbol_report.sort_values(
            by=["profit_factor", "net_profit"],
            ascending=False
        ).iloc[0]["symbol"]

    def worst_symbol(self):
        symbol_report = self.by_symbol()

        if symbol_report.empty:
            return ""

        return symbol_report.sort_values(
            by=["profit_factor", "net_profit"],
            ascending=True
        ).iloc[0]["symbol"]