import pandas as pd


class SignalEngine:

    def __init__(self, csv_path):

        self.csv_path = csv_path
        self.df = None

    def load_csv(self):

        print("Loading CSV...")
        self.df = pd.read_csv(self.csv_path)

    def generate(self):

        print("Generating signals...")

        self.df["Signal"] = "HOLD"

        buy = (
            (self.df["EMA20"] > self.df["EMA50"]) &
            (self.df["RSI14"] < 70)
        )

        sell = (
            (self.df["EMA20"] < self.df["EMA50"]) &
            (self.df["RSI14"] > 30)
        )

        self.df.loc[buy, "Signal"] = "BUY"
        self.df.loc[sell, "Signal"] = "SELL"

    def save(self):

        self.df.to_csv(self.csv_path, index=False)

        print("Saved ->", self.csv_path)


def main():

    engine = SignalEngine(
        "data/BTCUSDT/15m/BTCUSDT_15m.csv"
    )

    engine.load_csv()
    engine.generate()
    engine.save()


if __name__ == "__main__":

    main()