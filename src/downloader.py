from pathlib import Path

import pandas as pd
from binance.client import Client


class BinanceDownloader:

    def __init__(self):

        self.client = Client()

    def download(
        self,
        symbol,
        interval,
        limit=1000
    ):

        klines = self.client.get_klines(

            symbol=symbol,
            interval=interval,
            limit=limit

        )

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

        df = pd.DataFrame(

            klines,
            columns=columns

        )

        return df


def save_csv(df, symbol, interval):

    folder = Path("data") / symbol / interval

    folder.mkdir(

        parents=True,
        exist_ok=True

    )

    filename = folder / f"{symbol}_{interval}.csv"

    df.to_csv(

        filename,
        index=False

    )

    print("Saved ->", filename)


def main():

    client = BinanceDownloader()

    df = client.download(

        "BTCUSDT",
        Client.KLINE_INTERVAL_15MINUTE,
        1000

    )

    save_csv(

        df,
        "BTCUSDT",
        "15m"

    )


if __name__ == "__main__":

    main()