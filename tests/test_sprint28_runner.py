from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STRATEGY_LAB = PROJECT_ROOT / "strategy_lab"
if str(STRATEGY_LAB) not in sys.path:
    sys.path.insert(0, str(STRATEGY_LAB))

from run_sprint28 import (  # noqa: E402
    ModuleResult,
    REQUIRED_OUTPUTS,
    Sprint28RunnerError,
    _validate_outputs,
    run_sprint28,
)


class Sprint28RunnerTests(unittest.TestCase):
    def test_validate_outputs_reports_missing_and_empty_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / "ok.txt"
            existing.write_text("ok", encoding="utf-8")
            empty = root / "empty.txt"
            empty.write_text("", encoding="utf-8")

            invalid = _validate_outputs(root, ("ok.txt", "empty.txt", "missing.txt"))

            self.assertEqual(invalid, ["empty.txt", "missing.txt"])

    def test_run_sprint28_writes_pass_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "strategy_lab").mkdir()
            for relative in REQUIRED_OUTPUTS:
                output = root / relative
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text("generated", encoding="utf-8")

            fake_result = ModuleResult("x", ["python"], 0, "ok", "")
            with patch("run_sprint28._run_command", return_value=fake_result):
                report = run_sprint28(root)

            self.assertEqual(report["status"], "PASS")
            validation = json.loads(
                (root / "strategy_lab" / "sprint28_validation.json").read_text(encoding="utf-8")
            )
            self.assertEqual(validation["status"], "PASS")
            self.assertEqual(len(validation["completed_modules"]), 4)

    def test_run_sprint28_writes_fail_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "strategy_lab").mkdir()
            with patch(
                "run_sprint28._run_command",
                side_effect=Sprint28RunnerError("module failed"),
            ):
                with self.assertRaises(Sprint28RunnerError):
                    run_sprint28(root)

            validation = json.loads(
                (root / "strategy_lab" / "sprint28_validation.json").read_text(encoding="utf-8")
            )
            self.assertEqual(validation["status"], "FAIL")
            self.assertIn("module failed", validation["error"])


if __name__ == "__main__":
    unittest.main()
