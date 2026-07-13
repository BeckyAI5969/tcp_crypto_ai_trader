from pathlib import Path
import tempfile
import unittest
import sys

import pandas as pd

MODULE_DIR = Path(__file__).resolve().parents[1] / "strategy_lab" / "database"
sys.path.insert(0, str(MODULE_DIR))

from master_trade_database import (
    build_master_trade_history,
    discover_trade_journals,
    validate_master_frame,
)


class MasterTradeDatabaseTests(unittest.TestCase):
    def _write_journal(
        self,
        path: Path,
        version_shift: float = 0.0,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [
                {
                    "symbol": "BTCUSDT",
                    "entry_time": "2026-01-01T00:00:00Z",
                    "exit_time": "2026-01-01T01:00:00Z",
                    "entry_price": 100 + version_shift,
                    "exit_price": 102 + version_shift,
                    "quantity": 1,
                    "net_profit": 2,
                    "exit_reason": "TAKE_PROFIT",
                },
                {
                    "symbol": "ETHUSDT",
                    "entry_time": "2026-01-02T00:00:00Z",
                    "exit_time": "2026-01-02T01:00:00Z",
                    "entry_price": 50 + version_shift,
                    "exit_price": 49 + version_shift,
                    "quantity": 2,
                    "net_profit": -2,
                    "exit_reason": "STOP_LOSS",
                },
            ]
        ).to_csv(path, index=False)

    def test_discovers_and_merges_multiple_versions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            v010 = root / "reports" / "backtest_v0.1.0" / "trade_journal.csv"
            v011 = (
                root
                / "reports"
                / "strategy_lab"
                / "v0.1.1"
                / "trade_journal.csv"
            )
            self._write_journal(v010)
            self._write_journal(v011, version_shift=10)

            discovered = discover_trade_journals(root)
            self.assertEqual(len(discovered), 2)

            output = (
                root
                / "strategy_lab"
                / "history"
                / "master_trade_history.csv"
            )
            master, report = build_master_trade_history(root, output_path=output)

            self.assertTrue(output.exists())
            self.assertEqual(len(master), 4)
            self.assertEqual(
                set(master["strategy_version"]),
                {"v0.1.0", "v0.1.1"},
            )
            self.assertTrue(report["validation"]["passed"])
            self.assertTrue(report["validation"]["source_gate_passed"])

    def test_deduplicates_same_trade(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            journal = root / "reports" / "backtest_v0.1.0" / "trade_journal.csv"
            self._write_journal(journal)

            duplicate = pd.read_csv(journal)
            duplicate = pd.concat(
                [duplicate, duplicate.iloc[[0]]],
                ignore_index=True,
            )
            duplicate.to_csv(journal, index=False)

            master, report = build_master_trade_history(root)
            self.assertEqual(len(master), 2)
            self.assertEqual(
                report["source_results"][0]["duplicate_rows_removed"],
                1,
            )
            self.assertTrue(report["validation"]["passed"])

    def test_skips_invalid_schema_and_fails_source_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            invalid = root / "reports" / "backtest_v0.1.0" / "trade_journal.csv"
            invalid.parent.mkdir(parents=True)
            pd.DataFrame(
                [{"symbol": "BTCUSDT", "net_profit": 10}]
            ).to_csv(invalid, index=False)

            master, report = build_master_trade_history(root)
            self.assertEqual(len(master), 0)
            self.assertEqual(report["sources_loaded"], 0)
            self.assertFalse(report["validation"]["passed"])
            self.assertFalse(report["validation"]["source_gate_passed"])

    def test_invalid_time_order_is_removed_during_normalization(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            journal = root / "reports" / "backtest_v0.1.0" / "trade_journal.csv"
            journal.parent.mkdir(parents=True)
            pd.DataFrame(
                [
                    {
                        "symbol": "BTCUSDT",
                        "entry_time": "2026-01-02T00:00:00Z",
                        "exit_time": "2026-01-01T00:00:00Z",
                        "entry_price": 100,
                        "exit_price": 90,
                        "net_profit": -10,
                    }
                ]
            ).to_csv(journal, index=False)

            master, report = build_master_trade_history(root)
            self.assertTrue(master.empty)
            self.assertFalse(report["validation"]["passed"])

    def test_validate_empty_frame_fails(self):
        frame = pd.DataFrame(
            columns=[
                "trade_id",
                "strategy_version",
                "source_file",
                *sorted(REQUIRED_TEST_COLUMNS),
            ]
        )
        result = validate_master_frame(frame)
        self.assertFalse(result["passed"])
        self.assertEqual(result["row_count"], 0)


REQUIRED_TEST_COLUMNS = {
    "symbol",
    "entry_time",
    "exit_time",
    "entry_price",
    "exit_price",
    "net_profit",
}


if __name__ == "__main__":
    unittest.main(verbosity=2)
