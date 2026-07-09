import json
from pathlib import Path

import pandas as pd

from src.portfolio_metrics import PortfolioMetrics


class PaperReport:

    def __init__(self):
        self.output_dir = Path("paper")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        orders,
        positions,
        equity_history,
    ):

        orders_df = pd.DataFrame(orders)
        positions_df = pd.DataFrame(positions)
        equity_df = pd.DataFrame(equity_history)

        closed_positions = positions_df[
            positions_df["status"] == "CLOSED"
        ].copy()

        if closed_positions.empty:
            trades_df = pd.DataFrame(
                columns=["profit"]
            )
        else:
            trades_df = closed_positions.rename(
                columns={
                    "realized_pnl": "profit"
                }
            )

        summary = PortfolioMetrics.summarize(
            trades_df,
            equity_df
        )

        orders_df.to_csv(
            self.output_dir / "paper_orders.csv",
            index=False,
        )

        positions_df.to_csv(
            self.output_dir / "paper_positions.csv",
            index=False,
        )

        equity_df.to_csv(
            self.output_dir / "paper_equity.csv",
            index=False,
        )

        with open(
            self.output_dir / "paper_summary.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                summary,
                f,
                indent=4,
            )

        print("=" * 70)
        print("TCP PAPER TRADING REPORT")
        print("=" * 70)

        for k, v in summary.items():
            print(f"{k:25s}: {v}")

        print("=" * 70)
        print("Saved ->", self.output_dir)
        print("=" * 70)