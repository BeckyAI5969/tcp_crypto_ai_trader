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

        total_trades = 0
        wins = 0

        entry_price = 0

        for _, row in self.df.iterrows():

            price = row["close"]

            # ใช้ AI_SIGNAL แทน Decision
            signal = row["AI_SIGNAL"]

            if signal == "BUY" and position == 0:

                position = cash / price
                entry_price = price
                cash = 0

            elif signal == "SELL" and position > 0:

                cash = position * price

                if price > entry_price:
                    wins += 1

                total_trades += 1

                position = 0
                entry_price = 0

        if position > 0:
            cash = position * self.df.iloc[-1]["close"]

        total_return = ((cash - self.initial_cash) / self.initial_cash) * 100

        win_rate = 0
        if total_trades > 0:
            win_rate = wins / total_trades * 100

        print("=" * 40)
        print("Backtest Result")
        print("=" * 40)
        print(f"Initial Cash : {self.initial_cash:.2f}")
        print(f"Final Equity : {cash:.2f}")
        print(f"Total Return : {total_return:.2f}%")
        print(f"Total Trades : {total_trades}")
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