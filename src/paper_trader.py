from datetime import datetime
from pathlib import Path

import pandas as pd

from config.symbols import SYMBOLS
from src.paper_execution import PaperExecutionEngine
from src.paper_portfolio import PaperPortfolio
from src.paper_report import PaperReport


class PaperTrader:

    def __init__(self):
        self.initial_capital = 100000
        self.capital_per_trade_pct = 0.10

        self.execution = PaperExecutionEngine()
        self.portfolio = PaperPortfolio(
            initial_capital=self.initial_capital
        )

        self.data_folder = Path("data")

    def run_once(self):
        print("=" * 70)
        print("TCP PAPER TRADER")
        print("=" * 70)

        for symbol in SYMBOLS:
            csv_path = self.data_folder / symbol / "15m" / f"{symbol}_15m.csv"

            if not csv_path.exists():
                print(symbol, "CSV not found -> skipped")
                continue

            df = pd.read_csv(csv_path)

            if df.empty:
                print(symbol, "CSV empty -> skipped")
                continue

            latest = df.iloc[-1]

            price = float(latest["close"])
            signal = str(latest.get("Signal", "WAIT"))
            score = float(latest.get("AI_SCORE", 0))

            print(symbol, "Signal:", signal, "Score:", score, "Price:", price)

            if signal != "BUY":
                continue

            if score < 80:
                continue

            capital_required = self.initial_capital * self.capital_per_trade_pct
            quantity = round(capital_required / price, 6)

            if not self.portfolio.open_position(capital_required):
                print(symbol, "Not enough cash")
                continue

            position = self.execution.execute_order(
                symbol=symbol,
                side="BUY",
                quantity=quantity,
                price=price,
            )

            print("Paper position opened:", position.to_dict(price))

        unrealized = 0.0

        for position in self.execution.open_positions():
            csv_path = self.data_folder / position.symbol / "15m" / f"{position.symbol}_15m.csv"
            df = pd.read_csv(csv_path)
            current_price = float(df.iloc[-1]["close"])

            unrealized += position.unrealized_pnl(current_price)

        self.portfolio.record(
            timestamp=datetime.utcnow().isoformat(),
            unrealized_pnl=unrealized,
            open_positions=len(self.execution.open_positions()),
        )

        PaperReport().generate(
            orders=self.execution.order_history(),
            positions=[
                p.to_dict()
                for p in self.execution.positions
            ],
            equity_history=self.portfolio.history(),
        )

        print("=" * 70)
        print("SPRINT 10 COMPLETED")
        print("=" * 70)


def main():
    PaperTrader().run_once()


if __name__ == "__main__":
    main()