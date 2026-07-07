import pandas as pd
from pathlib import Path
from binance.client import Client


class BinanceRestEngine:

    def __init__(self, symbol="BTCUSDT", interval="15m", limit=200):
        self.symbol = symbol
        self.interval = interval
        self.limit = limit
        self.client = Client()

    def fetch_klines(self):
        print("Fetching live candles from Binance REST...")

        klines = self.client.get_klines(
            symbol=self.symbol,
            interval=self.interval,
            limit=self.limit
        )

        df = pd.DataFrame(klines, columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore"
        ])

        numeric_cols = [
            "open", "high", "low", "close", "volume",
            "quote_volume", "taker_buy_base", "taker_buy_quote"
        ]

        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")

        return df

    def save_csv(self, df):
        folder = Path(f"data/{self.symbol}/{self.interval}")
        folder.mkdir(parents=True, exist_ok=True)

        file_path = folder / f"{self.symbol}_{self.interval}.csv"

        df.to_csv(file_path, index=False)

        print("Saved ->", file_path)
        print("Total rows ->", len(df))

    def run(self):
        df = self.fetch_klines()
        self.save_csv(df)


def main():
    engine = BinanceRestEngine(
        symbol="BTCUSDT",
        interval="15m",
        limit=200
    )

    engine.run()


if __name__ == "__main__":
    main()