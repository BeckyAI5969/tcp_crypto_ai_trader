import json
from datetime import datetime
from pathlib import Path

import pandas as pd


class PaperReport:

    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        self.report_file = self.log_dir / "paper_report.json"

    def save(self, portfolio, logger):
        portfolio_summary = portfolio.summary()
        trades = logger.load()

        closed = self._closed_trades(trades)

        wins = 0
        losses = 0
        breakeven = 0

        gross_profit = 0.0
        gross_loss = 0.0
        net_profit = 0.0

        total_fees = 0.0
        total_funding = 0.0

        average_win = 0.0
        average_loss = 0.0
        average_holding_seconds = 0.0

        if not closed.empty:
            pnl = pd.to_numeric(
                closed.get("realized_pnl"),
                errors="coerce",
            ).fillna(0.0)

            wins = int((pnl > 0).sum())
            losses = int((pnl < 0).sum())
            breakeven = int((pnl == 0).sum())

            gross_profit = float(
                pnl[pnl > 0].sum()
            )
            gross_loss = float(
                pnl[pnl < 0].sum()
            )
            net_profit = float(pnl.sum())

            if "entry_fee" in closed.columns:
                total_fees += float(
                    pd.to_numeric(
                        closed["entry_fee"],
                        errors="coerce",
                    ).fillna(0.0).sum()
                )

            if "exit_fee" in closed.columns:
                total_fees += float(
                    pd.to_numeric(
                        closed["exit_fee"],
                        errors="coerce",
                    ).fillna(0.0).sum()
                )

            if "funding_fee" in closed.columns:
                total_funding = float(
                    pd.to_numeric(
                        closed["funding_fee"],
                        errors="coerce",
                    ).fillna(0.0).sum()
                )

            if wins > 0:
                average_win = float(
                    pnl[pnl > 0].mean()
                )

            if losses > 0:
                average_loss = float(
                    pnl[pnl < 0].mean()
                )

            if "holding_seconds" in closed.columns:
                average_holding_seconds = float(
                    pd.to_numeric(
                        closed["holding_seconds"],
                        errors="coerce",
                    ).fillna(0.0).mean()
                )

        closed_trades = wins + losses + breakeven

        win_rate = (
            wins / closed_trades * 100
            if closed_trades > 0
            else 0.0
        )

        profit_factor = (
            gross_profit / abs(gross_loss)
            if gross_loss < 0
            else 0.0
        )

        expectancy = (
            net_profit / closed_trades
            if closed_trades > 0
            else 0.0
        )

        open_positions = [
            position.to_dict()
            for position in portfolio.get_open_positions()
        ]

        closed_positions = [
            position.to_dict()
            for position in portfolio.get_closed_positions()
        ]

        report = {
            "updated_at": datetime.now().isoformat(),
            "mode": "PAPER_LEVERAGED",
            "portfolio": {
                **portfolio_summary,
                "open_position_details": open_positions,
                "closed_position_details": closed_positions,
            },
            "statistics": {
                "closed_trades": closed_trades,
                "wins": wins,
                "losses": losses,
                "breakeven": breakeven,
                "win_rate_pct": round(win_rate, 4),
                "gross_profit": round(gross_profit, 8),
                "gross_loss": round(gross_loss, 8),
                "net_profit": round(net_profit, 8),
                "profit_factor": round(
                    profit_factor,
                    8,
                ),
                "expectancy_per_trade": round(
                    expectancy,
                    8,
                ),
                "average_win": round(
                    average_win,
                    8,
                ),
                "average_loss": round(
                    average_loss,
                    8,
                ),
                "average_holding_seconds": round(
                    average_holding_seconds,
                    2,
                ),
                "total_fees": round(
                    total_fees,
                    8,
                ),
                "total_funding_fee": round(
                    total_funding,
                    8,
                ),
                "total_log_events": int(len(trades)),
            },
        }

        temporary_file = self.report_file.with_suffix(
            ".json.tmp"
        )

        with open(
            temporary_file,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False,
            )

        temporary_file.replace(self.report_file)

        return report

    @staticmethod
    def _closed_trades(trades):
        if (
            trades.empty
            or "event" not in trades.columns
        ):
            return trades.iloc[0:0]

        return trades[
            trades["event"] == "CLOSE"
        ].copy()