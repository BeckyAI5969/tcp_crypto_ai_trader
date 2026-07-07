import pandas as pd


class PerformanceEngine:
    def __init__(self, csv_path, initial_cash=10000):
        self.csv_path = csv_path
        self.initial_cash = initial_cash
        self.df = None

    def load_csv(self):
        print("Loading CSV...")
        self.df = pd.read_csv(self.csv_path)

    def analyze(self):
        print("Analyzing performance...")

        cash = self.initial_cash
        position = 0
        entry_price = 0
        equity_curve = []
        trades = []

        for _, row in self.df.iterrows():
            price = row["close"]
            decision = row["Decision"]

            if decision == "BUY" and position == 0:
                position = cash / price
                entry_price = price
                cash = 0

            elif decision == "SELL" and position > 0:
                cash = position * price
                profit_pct = ((price - entry_price) / entry_price) * 100
                trades.append(profit_pct)
                position = 0
                entry_price = 0

            equity = cash + (position * price)
            equity_curve.append(equity)

        if position > 0:
            cash = position * self.df.iloc[-1]["close"]

        total_return = ((cash - self.initial_cash) / self.initial_cash) * 100

        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t <= 0]

        win_rate = (len(wins) / len(trades) * 100) if trades else 0
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss else 0

        peak = equity_curve[0] if equity_curve else self.initial_cash
        max_drawdown = 0

        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = ((peak - equity) / peak) * 100
            max_drawdown = max(max_drawdown, drawdown)

        print("=" * 45)
        print("Performance Analytics")
        print("=" * 45)
        print(f"Initial Cash   : {self.initial_cash:.2f}")
        print(f"Final Equity   : {cash:.2f}")
        print(f"Total Return   : {total_return:.2f}%")
        print(f"Total Trades   : {len(trades)}")
        print(f"Win Rate       : {win_rate:.2f}%")
        print(f"Average Win    : {avg_win:.2f}%")
        print(f"Average Loss   : {avg_loss:.2f}%")
        print(f"Profit Factor  : {profit_factor:.2f}")
        print(f"Max Drawdown   : {max_drawdown:.2f}%")
        print("=" * 45)


def main():
    engine = PerformanceEngine(
        "data/BTCUSDT/15m/BTCUSDT_15m.csv",
        initial_cash=10000
    )

    engine.load_csv()
    engine.analyze()


if __name__ == "__main__":
    main()