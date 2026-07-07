import time
import subprocess
from datetime import datetime


class RealtimeEngine:

    def __init__(self, interval=60):
        self.interval = interval

    def run_step(self, name, command):
        print("=" * 60)
        print(f"Running: {name}")
        print("=" * 60)

        result = subprocess.run(command, shell=True)

        if result.returncode != 0:
            print(f"ERROR: {name} failed")
            return False

        print(f"Completed: {name}")
        return True

    def run_once(self):
        print("=" * 60)
        print(datetime.now())
        print("TCP Crypto AI Trader - Realtime Pipeline")
        print("=" * 60)

        steps = [
            ("Binance REST Engine", "py src/binance_rest_engine.py"),
            ("Indicator Engine", "py src/indicator_engine.py"),
            ("Signal Engine", "py src/signal_engine.py"),
            ("Strategy Engine", "py src/strategy_engine.py"),
            ("Explain Engine", "py src/explain_engine.py"),
            ("Decision Engine", "py src/decision_engine.py"),
            ("Risk Manager", "py src/risk_manager.py"),
            ("Position Manager", "py src/position_manager.py"),
            ("Trade Logger", "py src/trade_logger.py"),
            ("LINE Alert", "py src/line_alert.py"),
        ]

        for name, command in steps:
            success = self.run_step(name, command)
            if not success:
                break

    def run(self):
        while True:
            self.run_once()

            print()
            print(f"Sleeping {self.interval} seconds")
            print()

            time.sleep(self.interval)


def main():
    engine = RealtimeEngine(interval=60)
    engine.run()


if __name__ == "__main__":
    main()