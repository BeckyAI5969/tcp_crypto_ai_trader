import subprocess
import sys


class AITrader:

    def run_step(self, name, command):
        print("=" * 50)
        print(f"Running: {name}")
        print("=" * 50)

        result = subprocess.run(command, shell=True)

        if result.returncode != 0:
            print(f"ERROR: {name} failed")
            sys.exit(1)

        print(f"Completed: {name}")

    def run(self):
        print("TCP Crypto AI Trader Started")

        self.run_step("Update Data", "py src/update_engine.py")
        self.run_step("Indicator Engine", "py src/indicator_engine.py")
        self.run_step("Signal Engine", "py src/signal_engine.py")
        self.run_step("Strategy Engine", "py src/strategy_engine.py")
        self.run_step("Explain Engine", "py src/explain_engine.py")
        self.run_step("Optimizer Engine", "py src/optimizer_engine.py")
        self.run_step("Decision Engine", "py src/decision_engine.py")
        self.run_step("Backtest Engine", "py src/backtest_engine.py")
        self.run_step("Performance Engine", "py src/performance_engine.py")

        print("=" * 50)
        print("TCP Crypto AI Trader Completed")
        print("=" * 50)


def main():
    trader = AITrader()
    trader.run()


if __name__ == "__main__":
    main()