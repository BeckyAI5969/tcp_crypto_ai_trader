import pandas as pd
from pathlib import Path


class BacktestEngine:

    def __init__(self, csv_path="data/BTCUSDT/15m/BTCUSDT_15m.csv"):
        self.csv_path = Path(csv_path)
        self.balance = 5000
        self.risk_per_trade = 0.01
        self.take_profit_pct = 0.03
        self.stop_loss_pct = -0.015

    def run(self):
        if not self.csv_path.exists():
            print("CSV file not found.")
            return

        df = pd.read_csv(self.csv_path)
        trades = []
        in_position = False
        entry_price = 0

        for i in range(len(df)):
            row = df.iloc[i]

            price = float(row["close"])
            signal = str(row.get("Signal", "WAIT"))
            score = float(row.get("AI_SCORE", 0))

            if (
                not in_position
                and signal == "BUY"
                and score >= 85
            ):
                in_position = True
                entry_price = price

            elif in_position:
                profit_pct = (price - entry_price) / entry_price

                if (
                    profit_pct >= self.take_profit_pct
                    or profit_pct <= self.stop_loss_pct
                ):
                    profit = (
                        self.balance
                        * self.risk_per_trade
                        * (profit_pct / abs(self.stop_loss_pct))
                    )

                    trades.append({
                        "entry": entry_price,
                        "exit": price,
                        "profit": round(profit, 2)
                    })

                    in_position = False

        if not trades:
            print("No trades found.")
            return

        result = pd.DataFrame(trades)

        total_trades = len(result)
        wins = result[result["profit"] > 0]
        losses = result[result["profit"] < 0]

        win_rate = len(wins) / total_trades * 100
        gross_profit = wins["profit"].sum()
        gross_loss = losses["profit"].sum()
        net_profit = result["profit"].sum()
        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else "Infinity"

        result["equity"] = result["profit"].cumsum()
        result["peak"] = result["equity"].cummax()
        result["drawdown"] = result["equity"] - result["peak"]
        max_drawdown = result["drawdown"].min()

        print("=" * 50)
        print("Backtest Report")
        print("=" * 50)
        print("Total Trades  :", total_trades)
        print("Win Rate      :", round(win_rate, 2), "%")
        print("Gross Profit  :", round(gross_profit, 2))
        print("Gross Loss    :", round(gross_loss, 2))
        print("Net Profit    :", round(net_profit, 2))
        print("Profit Factor :", profit_factor)
        print("Max Drawdown  :", round(max_drawdown, 2))
        print("=" * 50)


def main():
    engine = BacktestEngine()
    engine.run()


if __name__ == "__main__":
    main()