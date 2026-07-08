import time
from datetime import datetime

from src.binance_rest_engine import BinanceRestEngine
from src.indicator_engine import IndicatorEngine
from src.signal_engine import SignalEngine
from src.ai_trader import AITrader
from src.position_engine import PositionEngine
from src.line_alert import LineAlert


class SchedulerEngine:

    def __init__(self, interval_seconds=900):
        self.interval_seconds = interval_seconds
        self.csv_path = "data/BTCUSDT/15m/BTCUSDT_15m.csv"
        self.symbol = "BTCUSDT"

    def run_once(self):
        print("=" * 60)
        print("Scheduler Run - Safe Mode")
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

        current_position = PositionEngine().get_position(self.symbol)

        if current_position is not None:
            print("Safe Mode: Open position detected.")
            print("AITrader skipped to prevent duplicate order.")

            LineAlert().send(
                "⚠️ TCP Crypto AI Trader\nSafe Mode: Open position detected.\nNew order skipped."
            )
            return

        print("Safe Mode: No open position.")
        print("Running AITrader...")

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