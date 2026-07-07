import pandas as pd


class OptimizerEngine:

    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.df = None

    def load_csv(self):
        print("Loading CSV...")
        self.df = pd.read_csv(self.csv_path)

    def optimize(self):

        print("Optimizing strategy...")

        self.df["Confidence"] = 0

        # EMA Trend
        self.df.loc[
            self.df["EMA20"] > self.df["EMA50"],
            "Confidence"
        ] += 20

        self.df.loc[
            self.df["EMA50"] > self.df["EMA200"],
            "Confidence"
        ] += 20

        # RSI

        self.df.loc[
            (self.df["RSI14"] > 50) &
            (self.df["RSI14"] < 70),
            "Confidence"
        ] += 20

        # MACD

        self.df.loc[
            self.df["MACD"] >
            self.df["MACD_SIGNAL"],
            "Confidence"
        ] += 20

        # Volume

        self.df.loc[
            self.df["volume"] >
            self.df["VOLUME_MA20"],
            "Confidence"
        ] += 20

        self.df["AI_SIGNAL"] = "WAIT"

        self.df.loc[
            self.df["Confidence"] >= 80,
            "AI_SIGNAL"
        ] = "BUY"

        self.df.loc[
            self.df["Confidence"] <= 20,
            "AI_SIGNAL"
        ] = "SELL"

    def save(self):

        self.df.to_csv(
            self.csv_path,
            index=False
        )

        print("Saved ->", self.csv_path)


def main():

    engine = OptimizerEngine(
        "data/BTCUSDT/15m/BTCUSDT_15m.csv"
    )

    engine.load_csv()

    engine.optimize()

    engine.save()


if __name__ == "__main__":
    main()