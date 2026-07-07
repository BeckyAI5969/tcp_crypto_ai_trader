import pandas as pd


class SignalEngine:

    def __init__(self, csv_path):

        self.csv_path = csv_path
        self.df = None

        # AI Weights
        self.weights = {
            "ema": 0.35,
            "rsi": 0.20,
            "macd": 0.25,
            "volume": 0.10,
            "atr": 0.10
        }

    def load_csv(self):

        print("Loading CSV...")
        self.df = pd.read_csv(self.csv_path)

    def generate(self):

        print("Generating Weighted AI Signals...")

        self.df["AI_SCORE"] = 0.0

        # EMA
        ema_score = (
            self.df["EMA20"] > self.df["EMA50"]
        ).astype(int)

        # RSI
        rsi_score = (
            (self.df["RSI14"] > 45) &
            (self.df["RSI14"] < 65)
        ).astype(int)

        # MACD
        if "MACD" in self.df.columns:
            macd_score = (
                self.df["MACD"] > 0
            ).astype(int)
        else:
            macd_score = 0

        # Volume
        if "Volume_MA20" in self.df.columns:
            volume_score = (
                self.df["volume"] >
                self.df["Volume_MA20"]
            ).astype(int)
        else:
            volume_score = 1

        # ATR
        if "ATR14" in self.df.columns:
            atr_score = (
                self.df["ATR14"] > 0
            ).astype(int)
        else:
            atr_score = 1

        self.df["AI_SCORE"] = (

            ema_score * self.weights["ema"] +

            rsi_score * self.weights["rsi"] +

            macd_score * self.weights["macd"] +

            volume_score * self.weights["volume"] +

            atr_score * self.weights["atr"]

        ) * 100

        self.df["Signal"] = "WAIT"

        self.df.loc[
            self.df["AI_SCORE"] >= 80,
            "Signal"
        ] = "BUY"

        self.df.loc[
            self.df["AI_SCORE"] <= 20,
            "Signal"
        ] = "SELL"

    def save(self):

        self.df.to_csv(
            self.csv_path,
            index=False
        )

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