import pandas as pd


class DecisionEngine:

    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.df = None

    def load_csv(self):
        print("Loading CSV...")
        self.df = pd.read_csv(self.csv_path)

    def make_decision(self):
        print("Calculating AI decision...")

        self.df["AI_SCORE"] = 0
        self.df["AI_DECISION"] = "WAIT"

        self.df.loc[self.df["EMA20"] > self.df["EMA50"], "AI_SCORE"] += 15
        self.df.loc[self.df["EMA50"] > self.df["EMA200"], "AI_SCORE"] += 20
        self.df.loc[(self.df["RSI14"] >= 45) & (self.df["RSI14"] <= 65), "AI_SCORE"] += 15
        self.df.loc[self.df["MACD"] > self.df["MACD_SIGNAL"], "AI_SCORE"] += 20
        self.df.loc[self.df["close"] > self.df["BB_MIDDLE"], "AI_SCORE"] += 10
        self.df.loc[self.df["volume"] > self.df["VOLUME_MA20"], "AI_SCORE"] += 10
        self.df.loc[self.df["ATR14"] > 0, "AI_SCORE"] += 10

        self.df.loc[self.df["AI_SCORE"] >= 80, "AI_DECISION"] = "BUY"
        self.df.loc[self.df["AI_SCORE"] <= 25, "AI_DECISION"] = "SELL"

    def save(self):
        self.df.to_csv(self.csv_path, index=False)
        print("Saved ->", self.csv_path)


def main():

    engine = DecisionEngine(
        "data/BTCUSDT/15m/BTCUSDT_15m.csv"
    )

    engine.load_csv()
    engine.make_decision()
    engine.save()


if __name__ == "__main__":
    main()