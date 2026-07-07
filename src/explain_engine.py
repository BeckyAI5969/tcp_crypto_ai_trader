import pandas as pd


class ExplainEngine:

    def __init__(self, csv_path):
        self.csv_path = csv_path

    def load_csv(self):
        print("Loading CSV...")
        self.df = pd.read_csv(self.csv_path)

    def generate(self):

        print("Generating explanations...")

        reasons = []
        confidence = []

        for _, row in self.df.iterrows():

            reason = []

            score = row["StrategyScore"]

            if row["EMA20"] > row["EMA50"]:
                reason.append("EMA Bullish")
            else:
                reason.append("EMA Bearish")

            if row["RSI14"] > 60:
                reason.append("Strong RSI")
            elif row["RSI14"] < 40:
                reason.append("Weak RSI")

            if row["MACD"] > row["MACD_SIGNAL"]:
                reason.append("MACD Bullish")
            else:
                reason.append("MACD Bearish")

            if row["volume"] > row["VOLUME_MA20"]:
                reason.append("High Volume")
            else:
                reason.append("Low Volume")

            reasons.append(", ".join(reason))
            confidence.append(min(score, 100))

        self.df["Reason"] = reasons
        self.df["Confidence"] = confidence

    def save(self):
        self.df.to_csv(self.csv_path, index=False)
        print("Saved ->", self.csv_path)


def main():

    engine = ExplainEngine(
        "data/BTCUSDT/15m/BTCUSDT_15m.csv"
    )

    engine.load_csv()
    engine.generate()
    engine.save()


if __name__ == "__main__":
    main()