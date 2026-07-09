from pathlib import Path
import json
import pandas as pd


class PortfolioValidator:

    def __init__(self, baseline_file="validation/baseline.json"):

        self.errors = []
        self.warnings = []

        self.baseline = {}

        baseline = Path(baseline_file)

        if baseline.exists():
            with open(baseline, "r", encoding="utf-8") as f:
                self.baseline = json.load(f)

    def validate(self,
                 portfolio_summary="research/portfolio_summary.json",
                 equity_curve="research/portfolio_equity_curve.csv"):

        self.validate_summary(portfolio_summary)

        self.validate_equity(equity_curve)

        return len(self.errors) == 0

    def validate_summary(self, file):

        file = Path(file)

        if not file.exists():

            self.errors.append(
                "portfolio_summary.json not found"
            )

            return

        with open(file, "r", encoding="utf-8") as f:

            data = json.load(f)

        expected = self.baseline.get("expected", {})

        portfolio_pf = data.get("profit_factor", 0)

        if portfolio_pf < expected.get("portfolio_pf_min", 0):

            self.errors.append(
                f"Portfolio PF ต่ำกว่า Baseline ({portfolio_pf})"
            )

        drawdown = abs(
            data.get("max_drawdown_pct", 0)
        )

        if drawdown > expected.get("drawdown_max", 100):

            self.errors.append(
                f"Drawdown สูงเกินเกณฑ์ ({drawdown}%)"
            )

    def validate_equity(self, file):

        file = Path(file)

        if not file.exists():

            self.errors.append(
                "portfolio_equity_curve.csv not found"
            )

            return

        df = pd.read_csv(file)

        if df.empty:

            self.errors.append(
                "Portfolio Equity Curve is empty"
            )

            return

        if "equity" not in df.columns:

            self.errors.append(
                "Missing equity column"
            )

            return

        if (df["equity"] < 0).any():

            self.errors.append(
                "Negative equity detected"
            )

    def report(self):

        return {

            "pass": len(self.errors) == 0,

            "errors": self.errors,

            "warnings": self.warnings,
        }