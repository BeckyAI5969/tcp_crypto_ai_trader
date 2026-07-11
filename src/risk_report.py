import json
from pathlib import Path
from datetime import datetime


class RiskReport:

    def __init__(self):

        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        self.report_file = self.log_dir / "risk_report.json"

    def save(
        self,
        risk_manager,
        portfolio_summary,
    ):

        risk_summary = risk_manager.summary()

        report = {

            "updated_at": datetime.now().isoformat(),

            "risk": {

                "daily_realized_pnl":
                    risk_summary["daily_realized_pnl"],

                "consecutive_losses":
                    risk_summary["consecutive_losses"],

                "cooldown_until":
                    risk_summary["cooldown_until"],

            },

            "portfolio": {

                "open_positions":
                    portfolio_summary["open_positions"],

                "closed_positions":
                    portfolio_summary["closed_positions"],

                "equity":
                    portfolio_summary["equity"],

                "realized_pnl":
                    portfolio_summary["realized_pnl"],

                "unrealized_pnl":
                    portfolio_summary["unrealized_pnl"],

                "win_rate":
                    portfolio_summary["win_rate"],

            }

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