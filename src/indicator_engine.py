from pathlib import Path
import pandas as pd
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import AverageTrueRange, BollingerBands


class IndicatorEngine:

    def __init__(self, csv_path=None):
        self.csv_path = Path(csv_path) if csv_path else None
        self.df = None

    def load_csv(self):
        print("Loading CSV...")
        self.df = pd.read_csv(self.csv_path)

        for col in ["open", "high", "low", "close", "volume"]:
            self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

    def calculate(self):
        print("Calculating indicators...")

        self.df["EMA20"] = EMAIndicator(self.df["close"], window=20).ema_indicator()
        self.df["EMA50"] = EMAIndicator(self.df["close"], window=50).ema_indicator()
        self.df["EMA200"] = EMAIndicator(self.df["close"], window=200).ema_indicator()

        self.df["RSI14"] = RSIIndicator(self.df["close"], window=14).rsi()

        macd = MACD(self.df["close"])
        self.df["MACD"] = macd.macd()
        self.df["MACD_SIGNAL"] = macd.macd_signal()
        self.df["MACD_HIST"] = macd.macd_diff()

        atr = AverageTrueRange(
            high=self.df["high"],
            low=self.df["low"],
            close=self.df["close"],
            window=14,
        )
        self.df["ATR14"] = atr.average_true_range()

        bb = BollingerBands(self.df["close"], window=20)
        self.df["BB_UPPER"] = bb.bollinger_hband()
        self.df["BB_MIDDLE"] = bb.bollinger_mavg()
        self.df["BB_LOWER"] = bb.bollinger_lband()

        self.df["VOLUME_MA20"] = self.df["volume"].rolling(window=20).mean()

    def calculate_dataframe(self, df):
        self.df = df.copy()

        for col in ["open", "high", "low", "close", "volume"]:
            self.df[col] = pd.to_numeric(self.df[col], errors="coerce")

        self.calculate()
        return self.df

    def save(self):
        if self.csv_path:
            self.df.to_csv(self.csv_path, index=False)
            print("Saved ->", self.csv_path)


def main():
    engine = IndicatorEngine("data/BTCUSDT/15m/BTCUSDT_15m.csv")
    engine.load_csv()
    engine.calculate()
    engine.save()


if __name__ == "__main__":
    main()