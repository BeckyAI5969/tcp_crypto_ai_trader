from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from strategy_lab.analyzers.root_cause_summary import (
    RootCauseSummaryError,
    build_summary,
    load_trades,
    run,
)


class RootCauseSummaryTests(unittest.TestCase):
    def _trades(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "trade_id": "a",
                    "strategy_version": "v1",
                    "symbol": "BTCUSDT",
                    "entry_time": "2026-01-01T00:00:00Z",
                    "exit_time": "2026-01-01T01:00:00Z",
                    "exit_reason": "STOP_LOSS",
                    "net_profit": -100.0,
                },
                {
                    "trade_id": "b",
                    "strategy_version": "v1",
                    "symbol": "BTCUSDT",
                    "entry_time": "2026-01-02T00:00:00Z",
                    "exit_time": "2026-01-02T01:00:00Z",
                    "exit_reason": "TAKE_PROFIT",
                    "net_profit": 50.0,
                },
                {
                    "trade_id": "c",
                    "strategy_version": "v1",
                    "symbol": "ETHUSDT",
                    "entry_time": "2026-01-03T00:00:00Z",
                    "exit_time": "2026-01-03T01:00:00Z",
                    "exit_reason": "STOP_LOSS",
                    "net_profit": -25.0,
                },
            ]
        )

    def test_build_summary_ranks_measured_loss_concentrations(self) -> None:
        trades = self._trades()
        trades["is_loss"] = trades["net_profit"] < 0
        model, findings = build_summary(trades, {"v1": {"trades": 3, "net_profit": -75.0}})
        self.assertEqual(model["trade_count"], 3)
        self.assertGreaterEqual(len(findings), 2)
        self.assertEqual(findings[0].priority, 1)
        self.assertEqual(findings[0].value, "STOP_LOSS")
        self.assertAlmostEqual(findings[0].loss_contribution_pct, 100.0)
        self.assertIn("not proof", findings[0].interpretation)

    def test_unknown_trade_version_is_rejected(self) -> None:
        trades = self._trades()
        trades["is_loss"] = trades["net_profit"] < 0
        with self.assertRaises(RootCauseSummaryError):
            build_summary(trades, {"v2": {}})

    def test_invalid_time_order_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trades.csv"
            frame = self._trades()
            frame.loc[0, "exit_time"] = "2025-12-31T23:00:00Z"
            frame.to_csv(path, index=False)
            with self.assertRaises(RootCauseSummaryError):
                load_trades(path)

    def test_repository_integration_writes_all_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            history = root / "strategy_lab" / "history"
            strategy = root / "strategy_lab" / "strategies" / "v1"
            history.mkdir(parents=True)
            strategy.mkdir(parents=True)
            self._trades().to_csv(history / "master_trade_history.csv", index=False)
            (strategy / "manifest.json").write_text(
                json.dumps({"version": "v1", "metrics": {"trades": 3, "net_profit": -75.0}}),
                encoding="utf-8",
            )

            model = run(root)
            output = root / "strategy_lab" / "analyzers" / "root_cause_summary"
            self.assertEqual(model["trade_count"], 3)
            self.assertTrue((output / "ROOT_CAUSE_SUMMARY.md").is_file())
            self.assertTrue((output / "root_cause_summary.json").is_file())
            self.assertTrue((output / "root_cause_findings.csv").is_file())
            payload = json.loads((output / "root_cause_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["strategy_versions"], ["v1"])


if __name__ == "__main__":
    unittest.main()
