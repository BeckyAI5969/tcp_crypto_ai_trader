from pathlib import Path

import pandas as pd
from binance.client import Client


class DataUpdateEngine:

    def __init__(self):
        self.client = Client()

    def load_existing_data(self, file_path):
        if Path(file_path).exists():
            return pd.read_csv(file_path)
        return pd.DataFrame()

    def download_latest_data(self, symbol, interval, limit=100):
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

        return pd.DataFrame(klines, columns=columns)

    def update_csv(self, symbol, interval_name, binance_interval):
        file_path = Path("data") / symbol / interval_name / f"{symbol}_{interval_name}.csv"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        old_df = self.load_existing_data(file_path)
        new_df = self.download_latest_data(symbol, binance_interval, limit=100)

        if old_df.empty:
            final_df = new_df
        else:
            final_df = pd.concat([old_df, new_df], ignore_index=True)
            final_df = final_df.drop_duplicates(subset=["open_time"])
            final_df = final_df.sort_values("open_time")

        final_df.to_csv(file_path, index=False)

        print(f"Updated -> {file_path}")
        print(f"Total rows -> {len(final_df)}")
        print("-" * 50)


def main():
    engine = DataUpdateEngine()

    symbols = [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
        "XRPUSDT",
        "ADAUSDT",
        "DOGEUSDT",
        "BNBUSDT"
    ]

    for symbol in symbols:
        engine.update_csv(
            symbol=symbol,
            interval_name="15m",
            binance_interval=Client.KLINE_INTERVAL_15MINUTE
        )


if __name__ == "__main__":
    main()