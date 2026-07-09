import pandas as pd
from pathlib import Path


class FinalBacktestReport:

    def __init__(self):

        self.walk_forward = Path("research/walk_forward_report.csv")
        self.optimizer = Path("logs/strategy_optimizer_lab.csv")

    def run(self):

        print("=" * 70)
        print("TCP FINAL AI BACKTEST REPORT")
        print("=" * 70)

        if not self.walk_forward.exists():
            print("walk_forward_quant_lab.csv not found")
            return

        df = pd.read_csv(self.walk_forward)

        print("Dataset")
        print("-" * 70)
        print("Rows :", len(df))

        if len(df) == 0:
            print("No data")
            return

        print()

        print("Overall Performance")
        print("-" * 70)

        print("Total Trades        :", int(df["trades"].sum()))
        print("Average Win Rate    :", round(df["win_rate"].mean(), 2), "%")
        print("Average PF          :", round(df["profit_factor"].mean(), 3))
        print("Average Net Profit  :", round(df["net_profit"].mean(), 2))
        print("Average Drawdown    :", round(df["max_drawdown"].mean(), 2))

        print()

        best_pf = df.sort_values(
            "profit_factor",
            ascending=False
        ).iloc[0]

        best_profit = df.sort_values(
            "net_profit",
            ascending=False
        ).iloc[0]

        lowest_dd = df.sort_values(
            "max_drawdown",
            ascending=False
        ).iloc[0]

        print("=" * 70)
        print("BEST PROFIT FACTOR")
        print("=" * 70)
        print(best_pf)

        print()

        print("=" * 70)
        print("BEST NET PROFIT")
        print("=" * 70)
        print(best_profit)

        print()

        print("=" * 70)
        print("LOWEST DRAWDOWN")
        print("=" * 70)
        print(lowest_dd)

        print()

        if self.optimizer.exists():

            print("=" * 70)
            print("BEST PARAMETERS")
            print("=" * 70)

            opt = pd.read_csv(self.optimizer)

            best = opt.sort_values(
                [
                    "profit_factor_score",
                    "net_profit"
                ],
                ascending=False
            ).iloc[0]

            cols = [
                "symbol",
                "min_score",
                "take_profit_pct",
                "stop_loss_pct",
                "trend_filter",
                "rsi_filter",
                "profit_factor",
                "net_profit",
                "win_rate"
            ]

            print(best[cols])

        print()

        print("=" * 70)
        print("FINAL STATUS")
        print("=" * 70)

        if df["profit_factor"].mean() >= 1.30:
            print("PASS")
            print("Strategy is ready for Demo Trading")
        else:
            print("NOT PASS")
            print("Need more optimization")

        print("=" * 70)


def main():

    FinalBacktestReport().run()


if __name__ == "__main__":
    main()