from pathlib import Path
import json
import pandas as pd


class PortfolioReport:

    def __init__(self):

        self.output_folder = Path("research")

        self.output_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        trades_df,
        equity_df,
        statistics,
    ):

        trades_file = self.output_folder / "portfolio_trade_log.csv"
        equity_file = self.output_folder / "portfolio_equity_curve.csv"
        summary_file = self.output_folder / "portfolio_summary.json"

        trades_df.to_csv(
            trades_file,
            index=False,
        )

        equity_df.to_csv(
            equity_file,
            index=False,
        )

        summary_file.write_text(
            json.dumps(
                statistics,
                indent=4,
            ),
            encoding="utf-8",
        )

        print("=" * 70)
        print("TCP PORTFOLIO REPORT")
        print("=" * 70)

        for key, value in statistics.items():
            print(f"{key:25s}: {value}")

        print("=" * 70)
        print("Trade Log   :", trades_file)
        print("Equity Curve:", equity_file)
        print("Summary     :", summary_file)
        print("=" * 70)