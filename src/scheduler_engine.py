import time
from datetime import datetime

from binance_rest_engine import BinanceRestEngine
from indicator_engine import IndicatorEngine
from signal_engine import SignalEngine
from ai_trader import AITrader


class SchedulerEngine:

    def __init__(self, interval_seconds=900):
        self.interval_seconds = interval_seconds
        self.csv_path = "data/BTCUSDT/15m/BTCUSDT_15m.csv"

    def run_once(self):
        print("=" * 60)
        print("Scheduler Run")
        print("Time:", datetime.now())
        print("=" * 60)

        BinanceRestEngine().run()

        indicator = IndicatorEngine(self.csv_path)
        indicator.load_csv()
        indicator.calculate()
        indicator.save()

        signal = SignalEngine(self.csv_path)
        signal.load_csv()
        signal.generate()
        signal.save()

        AITrader().run()

    def run_forever(self):
        while True:
            self.run_once()
            print(f"Sleeping {self.interval_seconds} seconds")
            time.sleep(self.interval_seconds)


def main():
    engine = SchedulerEngine(interval_seconds=900)
    engine.run_once()


if __name__ == "__main__":
    main()