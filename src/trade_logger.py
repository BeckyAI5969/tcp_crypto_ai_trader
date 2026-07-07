import csv
from pathlib import Path
from datetime import datetime


class TradeLogger:

    def __init__(self, log_path="logs/trade_history.csv"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log_trade(
        self,
        symbol,
        side,
        entry_price,
        exit_price,
        quantity,
        ai_score,
        signal,
        reason=""
    ):
        profit = self.calculate_profit(
            side=side,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity
        )

        row = {
            "time": datetime.now().isoformat(),
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "profit": profit,
            "ai_score": ai_score,
            "signal": signal,
            "reason": reason
        }

        file_exists = self.log_path.exists()

        with open(self.log_path, "a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=row.keys())

            if not file_exists:
                writer.writeheader()

            writer.writerow(row)

        print("=" * 50)
        print("Trade Logged")
        print("=" * 50)
        print(row)
        print("=" * 50)

        return row

    def calculate_profit(self, side, entry_price, exit_price, quantity):
        entry_price = float(entry_price)
        exit_price = float(exit_price)
        quantity = float(quantity)

        if side == "BUY":
            return round((exit_price - entry_price) * quantity, 4)

        if side == "SELL":
            return round((entry_price - exit_price) * quantity, 4)

        return 0


def main():
    logger = TradeLogger()

    logger.log_trade(
        symbol="BTCUSDT",
        side="BUY",
        entry_price=63200,
        exit_price=63500,
        quantity=0.08,
        ai_score=84,
        signal="EMA bullish + RSI strong",
        reason="Test trade logger"
    )


if __name__ == "__main__":
    main()