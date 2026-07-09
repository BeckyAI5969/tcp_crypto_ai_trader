from pathlib import Path
import pandas as pd


class PaperValidator:

    def __init__(self):

        self.errors = []
        self.warnings = []

    def validate(
        self,
        orders="paper/paper_orders.csv",
        positions="paper/paper_positions.csv",
        summary="paper/paper_summary.json",
    ):

        self.validate_orders(orders)

        self.validate_positions(positions)

        self.validate_summary(summary)

        return len(self.errors) == 0

    def validate_orders(self, file):

        file = Path(file)

        if not file.exists():
            self.errors.append("paper_orders.csv not found")
            return

        df = pd.read_csv(file)

        if df.empty:
            self.errors.append("No paper orders generated")
            return

        if "status" in df.columns:

            invalid = df[
                ~df["status"].isin(
                    [
                        "NEW",
                        "FILLED",
                        "CANCELLED",
                    ]
                )
            ]

            if len(invalid):

                self.errors.append(
                    f"Invalid order status ({len(invalid)})"
                )

    def validate_positions(self, file):

        file = Path(file)

        if not file.exists():

            self.errors.append(
                "paper_positions.csv not found"
            )

            return

        df = pd.read_csv(file)

        if df.empty:

            self.errors.append(
                "No paper positions"
            )

            return

        if "status" in df.columns:

            invalid = df[
                ~df["status"].isin(
                    [
                        "OPEN",
                        "CLOSED",
                    ]
                )
            ]

            if len(invalid):

                self.errors.append(
                    f"Invalid position status ({len(invalid)})"
                )

    def validate_summary(self, file):

        file = Path(file)

        if not file.exists():

            self.errors.append(
                "paper_summary.json not found"
            )

    def report(self):

        return {

            "pass": len(self.errors) == 0,

            "errors": self.errors,

            "warnings": self.warnings,
        }