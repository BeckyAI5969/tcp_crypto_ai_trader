import pandas as pd
from pathlib import Path


class PaperTradeLog:

    def __init__(self):
        self.folder = Path("paper")
        self.folder.mkdir(parents=True, exist_ok=True)

        self.orders_path = self.folder / "paper_orders.csv"
        self.positions_path = self.folder / "paper_positions.csv"
        self.equity_path = self.folder / "paper_equity.csv"

    def save_orders(self, orders):
        pd.DataFrame(orders).to_csv(self.orders_path, index=False)
        print("Saved orders ->", self.orders_path)

    def save_positions(self, positions):
        pd.DataFrame(positions).to_csv(self.positions_path, index=False)
        print("Saved positions ->", self.positions_path)

    def save_equity(self, equity_history):
        pd.DataFrame(equity_history).to_csv(self.equity_path, index=False)
        print("Saved equity ->", self.equity_path)