from pathlib import Path
import json


class RegressionValidator:

    def __init__(self, baseline="validation/baseline.json"):

        self.errors = []
        self.warnings = []

        with open(baseline, "r", encoding="utf-8") as f:
            self.baseline = json.load(f)

    def validate(
        self,
        portfolio_summary="research/portfolio_summary.json",
        paper_summary="paper/paper_summary.json",
    ):

        self.validate_portfolio(portfolio_summary)
        self.validate_paper(paper_summary)

        return len(self.errors) == 0

    def validate_portfolio(self, file):

        file = Path(file)

        if not file.exists():
            self.errors.append("portfolio_summary.json not found")
            return

        with open(file, "r", encoding="utf-8") as f:
            summary = json.load(f)

        expected = self.baseline["expected"]

        if summary.get("profit_factor", 0) < expected["portfolio_pf_min"]:
            self.errors.append(
                f"Portfolio PF ต่ำกว่า Baseline ({summary.get('profit_factor')})"
            )

        if summary.get("win_rate", 0) < expected["winrate_min"]:
            self.errors.append(
                f"Portfolio Win Rate ต่ำกว่า Baseline ({summary.get('win_rate')}%)"
            )

    def validate_paper(self, file):

        file = Path(file)

        if not file.exists():
            self.errors.append("paper_summary.json not found")
            return

        with open(file, "r", encoding="utf-8") as f:
            summary = json.load(f)

        trades = summary.get("total_trades", 0)

        if trades == 0:
            self.warnings.append(
                "Paper Trading ยังไม่มี Closed Trades"
            )

    def report(self):

        return {
            "pass": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
        }