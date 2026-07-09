from pathlib import Path
import json


class ReportValidator:

    def __init__(self, baseline="validation/baseline.json"):

        self.errors = []
        self.warnings = []

        with open(baseline, "r", encoding="utf-8") as f:
            self.baseline = json.load(f)

    def validate(self):

        expected = self.baseline["expected"]["reports_required"]

        for report in expected:

            found = False

            for folder in [
                Path("research"),
                Path("paper"),
                Path("validation"),
            ]:

                file = folder / report

                if file.exists():
                    found = True
                    break

            if not found:

                self.errors.append(
                    f"Missing report : {report}"
                )

        return len(self.errors) == 0

    def report(self):

        return {

            "pass": len(self.errors) == 0,

            "errors": self.errors,

            "warnings": self.warnings,
        }