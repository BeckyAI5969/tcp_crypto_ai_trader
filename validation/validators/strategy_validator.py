import json
from pathlib import Path


class StrategyValidator:

    def __init__(self, baseline_file="validation/baseline.json"):
        self.baseline_file = Path(baseline_file)
        self.errors = []
        self.warnings = []

        if self.baseline_file.exists():
            with open(self.baseline_file, "r", encoding="utf-8") as f:
                self.baseline = json.load(f)
        else:
            self.baseline = {}

    def validate(self, current_config):

        expected = self.baseline.get("expected", {})

        self._check_equal(
            "timeframe",
            current_config.get("timeframe"),
            self.baseline.get("timeframe"),
        )

        self._check_equal(
            "commission",
            current_config.get("commission"),
            self.baseline.get("commission"),
        )

        self._check_equal(
            "slippage",
            current_config.get("slippage"),
            self.baseline.get("slippage"),
        )

        self._check_equal(
            "initial_capital",
            current_config.get("initial_capital"),
            self.baseline.get("initial_capital"),
        )

        self._check_equal(
            "symbols",
            current_config.get("symbols"),
            self.baseline.get("symbols"),
        )

        return len(self.errors) == 0

    def _check_equal(self, name, current, expected):

        if current != expected:
            self.errors.append(
                f"{name} mismatch : expected={expected} current={current}"
            )

    def report(self):

        return {
            "pass": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
        }