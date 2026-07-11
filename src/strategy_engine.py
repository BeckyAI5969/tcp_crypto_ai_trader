import pandas as pd


class StrategyEngine:

    def __init__(self, csv_path=None):
        self.csv_path = csv_path
        self.df = None

    def load_csv(self):
        print("Loading CSV...")
        self.df = pd.read_csv(self.csv_path)

    def calculate_score(self):
        print("Calculating strategy score V2.1...")

        self.df["TrendScore"] = 0
        self.df["MomentumScore"] = 0
        self.df["VolumeScore"] = 0
        self.df["VolatilityScore"] = 0
        self.df["PullbackScore"] = 0
        self.df["StrategyScore"] = 0

        self.df["Decision"] = "WAIT"
        self.df["SignalStrength"] = "NONE"
        self.df["SignalReason"] = ""

        # Trend
        self.df.loc[self.df["EMA20"] > self.df["EMA50"], "TrendScore"] += 20
        self.df.loc[self.df["EMA50"] > self.df["EMA200"], "TrendScore"] += 15

        self.df.loc[self.df["EMA20"] < self.df["EMA50"], "TrendScore"] -= 20
        self.df.loc[self.df["EMA50"] < self.df["EMA200"], "TrendScore"] -= 15

        # Momentum
        self.df.loc[self.df["MACD"] > self.df["MACD_SIGNAL"], "MomentumScore"] += 15
        self.df.loc[self.df["MACD_HIST"] > 0, "MomentumScore"] += 10
        self.df.loc[(self.df["RSI14"] >= 45) & (self.df["RSI14"] <= 72), "MomentumScore"] += 10

        self.df.loc[self.df["MACD"] < self.df["MACD_SIGNAL"], "MomentumScore"] -= 15
        self.df.loc[self.df["MACD_HIST"] < 0, "MomentumScore"] -= 10
        self.df.loc[(self.df["RSI14"] >= 28) & (self.df["RSI14"] <= 55), "MomentumScore"] -= 10

        # Volume
        self.df.loc[self.df["volume"] > self.df["VOLUME_MA20"], "VolumeScore"] += 15

        # Volatility
        self.df.loc[self.df["ATR14"] > 0, "VolatilityScore"] += 10

        # Pullback / Entry quality
        self.df.loc[
            (self.df["close"] >= self.df["EMA20"] * 0.995)
            & (self.df["close"] <= self.df["EMA20"] * 1.02),
            "PullbackScore",
        ] += 10

        self.df.loc[
            (self.df["close"] <= self.df["EMA20"] * 1.005)
            & (self.df["close"] >= self.df["EMA20"] * 0.98),
            "PullbackScore",
        ] -= 10

        self.df["StrategyScore"] = (
            self.df["TrendScore"]
            + self.df["MomentumScore"]
            + self.df["VolumeScore"]
            + self.df["VolatilityScore"]
            + self.df["PullbackScore"]
        )

        # Long signal
        self.df.loc[
            self.df["StrategyScore"] >= 60,
            "Decision",
        ] = "BUY"

        # Short signal
        self.df.loc[
            self.df["StrategyScore"] <= -60,
            "Decision",
        ] = "SELL"

        # Strength
        self.df.loc[self.df["StrategyScore"].abs() >= 90, "SignalStrength"] = "HIGH"
        self.df.loc[
            (self.df["StrategyScore"].abs() >= 75)
            & (self.df["StrategyScore"].abs() < 90),
            "SignalStrength",
        ] = "STRONG"
        self.df.loc[
            (self.df["StrategyScore"].abs() >= 60)
            & (self.df["StrategyScore"].abs() < 75),
            "SignalStrength",
        ] = "NORMAL"

        self.df.loc[self.df["Decision"] == "BUY", "SignalReason"] = (
            "Trend/Momentum bullish with valid volatility"
        )
        self.df.loc[self.df["Decision"] == "SELL", "SignalReason"] = (
            "Trend/Momentum bearish with valid volatility"
        )
        self.df.loc[self.df["Decision"] == "WAIT", "SignalReason"] = (
            "No sufficient trading edge"
        )

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