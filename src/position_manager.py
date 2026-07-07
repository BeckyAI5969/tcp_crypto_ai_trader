import json
import pandas as pd
from pathlib import Path
from datetime import datetime


class PositionManager:

    def __init__(self, csv_path, position_path="logs/position.json"):
        self.csv_path = csv_path
        self.position_path = Path(position_path)
        self.df = None

    def load_csv(self):
        print("Loading CSV...")
        self.df = pd.read_csv(self.csv_path)

    def load_position(self):
        if self.position_path.exists():
            with open(self.position_path, "r") as file:
                return json.load(file)

        return {
            "status": "CLOSED",
            "symbol": "BTCUSDT",
            "entry_price": 0,
            "quantity": 0,
            "entry_time": ""
        }

    def save_position(self, position):
        self.position_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.position_path, "w") as file:
            json.dump(position, file, indent=4)

    def manage(self):
        print("Managing position...")

        latest = self.df.iloc[-1]
        position = self.load_position()

        price = latest["close"]
        decision = latest.get("AI_DECISION", "WAIT")
        score = latest.get("AI_SCORE", 0)

        print("=" * 45)
        print("Position Manager")
        print("=" * 45)
        print(f"Current Status : {position['status']}")
        print(f"AI Decision    : {decision}")
        print(f"AI Score       : {score}")
        print(f"Close Price    : {price:.2f}")

        if position["status"] == "CLOSED" and decision == "BUY":
            position = {
                "status": "OPEN",
                "symbol": "BTCUSDT",
                "entry_price": float(price),
                "quantity": 1,
                "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            print("Action         : OPEN POSITION")

        elif position["status"] == "OPEN" and decision == "SELL":
            pnl_pct = ((price - position["entry_price"]) / position["entry_price"]) * 100

            print("Action         : CLOSE POSITION")
            print(f"Entry Price    : {position['entry_price']:.2f}")
            print(f"PNL            : {pnl_pct:.2f}%")

            position = {
                "status": "CLOSED",
                "symbol": "BTCUSDT",
                "entry_price": 0,
                "quantity": 0,
                "entry_time": ""
            }

        else:
            print("Action         : HOLD / WAIT")

        self.save_position(position)

        print("=" * 45)
        print("Saved ->", self.position_path)

    def run(self):
        self.load_csv()
        self.manage()


def main():
    manager = PositionManager(
        "data/BTCUSDT/15m/BTCUSDT_15m.csv"
    )

    manager.run()


if __name__ == "__main__":
    main()