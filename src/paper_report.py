import json
from pathlib import Path
from datetime import datetime


class PaperReport:

    def __init__(self):

        self.report_dir = Path("logs")
        self.report_dir.mkdir(exist_ok=True)

        self.report_file = (
            self.report_dir / "paper_summary.json"
        )

    def save(
        self,
        portfolio,
        trade_logger,
    ):

        summary = portfolio.summary()

        report = {

            "generated_at":
                datetime.now().isoformat(),

            "mode":
                "PAPER",

            "total_trades":
                trade_logger.total_trades(),

            "open_positions":
                summary["open_positions"],

            "closed_positions":
                summary["closed_positions"],

            "realized_pnl":
                summary["realized_pnl"],

            "unrealized_pnl":
                summary["unrealized_pnl"],

            "equity":
                summary["equity"],

            "status":
                "RUNNING",

        }

        with open(
            self.report_file,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                report,
                f,
                indent=4,
                ensure_ascii=False,
            )

        return report