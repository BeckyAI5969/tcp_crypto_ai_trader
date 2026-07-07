import pandas as pd


class BacktestEngine:
    def __init__(self, csv_path, initial_cash=10000):
        self.csv_path = csv_path
        self.initial_cash = initial_cash
        self.df = None

    def load_csv(self):
        print("Loading CSV...")
        self.df = pd.read_csv(self.csv_path)

    def run(self):
        print("Running backtest...")

        cash = self.initial_cash
        position = 0
        entry_price = 0
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

        if position > 0:
            cash = position * self.df.iloc[-1]["close"]

        total_return = ((cash - self.initial_cash) / self.initial_cash) * 100
        win_trades = [t for t in trades if t > 0]
        win_rate = (len(win_trades) / len(trades) * 100) if trades else 0

        print("=" * 40)
        print("Backtest Result")
        print("=" * 40)
        print(f"Initial Cash : {self.initial_cash:.2f}")
        print(f"Final Equity : {cash:.2f}")
        print(f"Total Return : {total_return:.2f}%")
        print(f"Total Trades : {len(trades)}")
        print(f"Win Rate     : {win_rate:.2f}%")
        print("=" * 40)


def main():
    engine = BacktestEngine(
        "data/BTCUSDT/15m/BTCUSDT_15m.csv",
        initial_cash=10000
    )

    engine.load_csv()
    engine.run()


if __name__ == "__main__":
    main()