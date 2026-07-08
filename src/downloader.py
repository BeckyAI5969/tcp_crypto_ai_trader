from pathlib import Path
import time

import pandas as pd
from binance.client import Client

from config.symbols import SYMBOLS


class BinanceDownloader:

    def __init__(self):
        self.client = Client()

    def download_history(
        self,
        symbol,
        interval=Client.KLINE_INTERVAL_15MINUTE,
        target_bars=35000
    ):
        all_rows = []
        end_time = None

        print("=" * 60)
        print("Downloading:", symbol)
        print("Target bars:", target_bars)
        print("=" * 60)

        while len(all_rows) < target_bars:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=1000,
                endTime=end_time
            )

            if not klines:
                break

            all_rows = klines + all_rows
            end_time = klines[0][0] - 1

            print(symbol, "bars:", len(all_rows))

            time.sleep(0.2)

        columns = [
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
        ]

        df = pd.DataFrame(all_rows, columns=columns)
        df = df.drop_duplicates(subset=["open_time"])
        df = df.sort_values("open_time")
        df = df.tail(target_bars)

        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")

        return df


def save_csv(df, symbol, interval_name="15m"):
    folder = Path("data") / symbol / interval_name
    folder.mkdir(parents=True, exist_ok=True)

    filename = folder / f"{symbol}_{interval_name}.csv"
    df.to_csv(filename, index=False)

    print("Saved ->", filename)
    print("Rows  ->", len(df))


def main():
    downloader = BinanceDownloader()

    for symbol in SYMBOLS:
        df = downloader.download_history(
            symbol=symbol,
            interval=Client.KLINE_INTERVAL_15MINUTE,
            target_bars=35000
        )

        save_csv(df, symbol, "15m")


if __name__ == "__main__":
    main()