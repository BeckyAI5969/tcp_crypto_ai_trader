import pandas as pd
from pathlib import Path


class PerformanceEngine:

    def __init__(self, log_path="logs/trade_history.csv"):
        self.log_path = Path(log_path)

    def run(self):
        if not self.log_path.exists():
            print("No trade history found.")
            return None

        df = pd.read_csv(self.log_path)

        if df.empty:
            print("Trade history is empty.")
            return None

        df["profit"] = pd.to_numeric(df["profit"], errors="coerce").fillna(0)

        total_trades = len(df)
        wins = df[df["profit"] > 0]
        losses = df[df["profit"] < 0]

        winning_trades = len(wins)
        losing_trades = len(losses)

        win_rate = (winning_trades / total_trades) * 100 if total_trades else 0

        gross_profit = wins["profit"].sum()
        gross_loss = losses["profit"].sum()
        net_profit = df["profit"].sum()
        average_profit = df["profit"].mean()

        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else 0

        df["equity"] = df["profit"].cumsum()
        df["peak"] = df["equity"].cummax()
        df["drawdown"] = df["equity"] - df["peak"]
        max_drawdown = df["drawdown"].min()

        print("=" * 50)
        print("Performance Report")
        print("=" * 50)
        print("Total Trades   :", total_trades)
        print("Winning Trades :", winning_trades)
        print("Losing Trades  :", losing_trades)
        print("Win Rate       :", round(win_rate, 2), "%")
        print("Gross Profit   :", round(gross_profit, 4))
        print("Gross Loss     :", round(gross_loss, 4))
        print("Net Profit     :", round(net_profit, 4))
        print("Average Profit :", round(average_profit, 4))
        print("Profit Factor  :", round(profit_factor, 4))
        print("Max Drawdown   :", round(max_drawdown, 4))
        print("=" * 50)

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "gross_profit": round(gross_profit, 4),
            "gross_loss": round(gross_loss, 4),
            "net_profit": round(net_profit, 4),
            "average_profit": round(average_profit, 4),
            "profit_factor": round(profit_factor, 4),
            "max_drawdown": round(max_drawdown, 4),
        }


def main():
    engine = PerformanceEngine()
    engine.run()


if __name__ == "__main__":
    main()