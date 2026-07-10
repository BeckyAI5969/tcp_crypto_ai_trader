import json
from pathlib import Path
from datetime import datetime


class PaperReport:

    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        self.report_file = self.log_dir / "paper_report.json"

    def save(self, portfolio, logger):
        summary = portfolio.summary()
        df = logger.load()

        closed = (
            df[df["event"] == "CLOSE"]
            if not df.empty and "event" in df.columns
            else df.iloc[0:0]
        )

        wins = 0
        losses = 0
        gross_profit = 0.0
        gross_loss = 0.0
        net_profit = 0.0

        if not closed.empty and "realized_pnl" in closed.columns:
            pnl = closed["realized_pnl"].astype(float)

            wins = int((pnl > 0).sum())
            losses = int((pnl < 0).sum())

            gross_profit = round(float(pnl[pnl > 0].sum()), 4)
            gross_loss = round(float(pnl[pnl < 0].sum()), 4)
            net_profit = round(float(pnl.sum()), 4)

        total_closed = wins + losses

        win_rate = (
            round(wins / total_closed * 100, 2)
            if total_closed
            else 0.0
        )

        profit_factor = (
            round(gross_profit / abs(gross_loss), 4)
            if gross_loss < 0
            else 0.0
        )

        report = {
            "updated_at": datetime.now().isoformat(),
            "mode": "PAPER",
            "portfolio": summary,
            "statistics": {
                "closed_trades": total_closed,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "gross_profit": gross_profit,
                "gross_loss": gross_loss,
                "net_profit": net_profit,
                "profit_factor": profit_factor,
                "total_log_events": len(df),
            },
        }

        with open(self.report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)

        return report