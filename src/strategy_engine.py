import pandas as pd


class StrategyEngine:

    def __init__(self, csv_path=None):
        self.csv_path = csv_path
        self.df = None

    def load_csv(self):
        print("Loading CSV...")
        self.df = pd.read_csv(self.csv_path)

    def calculate_score(self):
        print("Calculating strategy score...")

        self.df["StrategyScore"] = 0
        self.df["Decision"] = "WAIT"

        self.df.loc[self.df["EMA20"] > self.df["EMA50"], "StrategyScore"] += 25
        self.df.loc[self.df["MACD"] > self.df["MACD_SIGNAL"], "StrategyScore"] += 25
        self.df.loc[(self.df["RSI14"] > 45) & (self.df["RSI14"] < 70), "StrategyScore"] += 20
        self.df.loc[self.df["close"] > self.df["BB_MIDDLE"], "StrategyScore"] += 15
        self.df.loc[self.df["volume"] > self.df["VOLUME_MA20"], "StrategyScore"] += 15

        self.df.loc[self.df["StrategyScore"] >= 70, "Decision"] = "BUY"
        self.df.loc[self.df["StrategyScore"] <= 30, "Decision"] = "SELL"

    def calculate_dataframe(self, df):
        self.df = df.copy()
        self.calculate_score()
        return self.df

    def save(self):
        if self.csv_path:
            self.df.to_csv(self.csv_path, index=False)
            print("Saved ->", self.csv_path)


def main():
    engine = StrategyEngine("data/BTCUSDT/15m/BTCUSDT_15m.csv")
    engine.load_csv()
    engine.calculate_score()
    engine.save()


if __name__ == "__main__":
    main()