"""
TCP Crypto AI Trader
Validation Engine
Sprint 10.5
"""

from pathlib import Path
import json

from validation.validators.data_validator import DataValidator
from validation.validators.strategy_validator import StrategyValidator
from validation.validators.portfolio_validator import PortfolioValidator
from validation.validators.paper_validator import PaperValidator
from validation.validators.report_validator import ReportValidator
from validation.validators.regression_validator import RegressionValidator

from validation.certificate_generator import CertificateGenerator


class ValidationEngine:

    def __init__(self):

        self.project_root = Path.cwd()

        self.result = {
            "data_integrity": False,
            "strategy_integrity": False,
            "portfolio_integrity": False,
            "paper_integrity": False,
            "report_integrity": False,
            "regression_integrity": False,
        }

        self.issues = []

    def add_result(self, key, report):

        self.result[key] = report["pass"]

        severity = "HIGH"

        if key == "paper_integrity":
            severity = "MEDIUM"

        for err in report["errors"]:
            self.issues.append(
                {
                    "module": key,
                    "severity": severity,
                    "type": "ERROR",
                    "message": err,
                }
            )

        for warn in report["warnings"]:
            self.issues.append(
                {
                    "module": key,
                    "severity": "LOW",
                    "type": "WARNING",
                    "message": warn,
                }
            )

    def run(self):

        print("=" * 70)
        print("TCP CRYPTO AI TRADER")
        print("VALIDATION ENGINE")
        print("=" * 70)

        #
        # Data
        #
        print("Running Data Validator...")

        data = DataValidator()

        data_ok = True

        data_folder = Path("data")

        csv_files = list(data_folder.rglob("*.csv"))

        if len(csv_files) == 0:

            data.errors.append("No CSV files found")

            data_ok = False

        else:

            for csv in csv_files:

                ok = data.validate(csv)

                if not ok:
                    data_ok = False

        self.add_result(
            "data_integrity",
            data.report(),
        )

        #
        # Strategy
        #
        print("Running Strategy Validator...")

        strategy = StrategyValidator()

        current_config = {
            "timeframe": "15m",
            "commission": 0.0004,
            "slippage": 0.0002,
            "initial_capital": 100000,
            "symbols": [
                "BTCUSDT",
                "ETHUSDT",
                "SOLUSDT",
                "XRPUSDT",
                "BNBUSDT",
            ],
        }

        strategy.validate(current_config)

        self.add_result(
            "strategy_integrity",
            strategy.report(),
        )

        #
        # Portfolio
        #
        print("Running Portfolio Validator...")

        portfolio = PortfolioValidator()

        portfolio.validate()

        self.add_result(
            "portfolio_integrity",
            portfolio.report(),
        )

        #
        # Paper
        #
        print("Running Paper Validator...")

        paper = PaperValidator()

        paper.validate()

        self.add_result(
            "paper_integrity",
            paper.report(),
        )

        #
        # Report
        #
        print("Running Report Validator...")

        report = ReportValidator()

        report.validate()

        self.add_result(
            "report_integrity",
            report.report(),
        )

        #
        # Regression
        #
        print("Running Regression Validator...")

        regression = RegressionValidator()

        regression.validate()

        self.add_result(
            "regression_integrity",
            regression.report(),
        )

        return self.finish()

    def finish(self):

        passed = sum(self.result.values())

        total = len(self.result)

        score = round(
            passed / total * 100,
            2,
        )

        summary = {
            "score": score,
            "passed": passed,
            "total": total,
            "result": self.result,
            "issues": self.issues,
        }

        summary_file = (
            Path("validation")
            / "validation_summary.json"
        )

        with open(
            summary_file,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                summary,
                f,
                indent=4,
                ensure_ascii=False,
            )

        CertificateGenerator().generate(summary)

        print()

        print("=" * 70)

        print("VALIDATION RESULT")

        print("=" * 70)

        for k, v in self.result.items():

            print(
                f"{k:30s}",
                "PASS" if v else "FAIL",
            )

        print()

        print(f"Overall Score : {score}%")

        print(f"Issues : {len(self.issues)}")

        print("=" * 70)

        return summary


def main():

    ValidationEngine().run()


if __name__ == "__main__":

    main()