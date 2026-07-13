"""Tests for Sprint 28 Module 28.2 Strategy Dashboard."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from strategy_lab.dashboard.strategy_dashboard import (
    DashboardError,
    build_dashboard_model,
    calculate_metrics,
    generate_dashboard,
    load_master_trades,
)


class StrategyDashboardUnitTests(unittest.TestCase):
    def test_calculate_metrics_uses_trade_sequence_for_drawdown(self) -> None:
        trades = pd.DataFrame({"net_profit": [100.0, -40.0, -80.0, 30.0]})
        metrics = calculate_metrics(trades)
        self.assertEqual(metrics.trades, 4)
        self.assertEqual(metrics.wins, 2)
        self.assertEqual(metrics.losses, 2)
        self.assertAlmostEqual(metrics.win_rate, 50.0)
        self.assertAlmostEqual(metrics.profit_factor or 0.0, 130.0 / 120.0)
        self.assertAlmostEqual(metrics.net_profit, 10.0)
        self.assertAlmostEqual(metrics.expectancy, 2.5)
        self.assertAlmostEqual(metrics.max_drawdown, -120.0)

    def test_build_model_rejects_trade_version_without_manifest(self) -> None:
        manifests = [self._manifest("v1")]
        trades = self._trades("v2")
        with self.assertRaisesRegex(DashboardError, "without manifests"):
            build_dashboard_model(manifests, trades)

    def test_load_master_trades_rejects_duplicate_trade_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "master.csv"
            trades = self._trades("v1")
            trades.loc[1, "trade_id"] = trades.loc[0, "trade_id"]
            trades.to_csv(path, index=False)
            with self.assertRaisesRegex(DashboardError, "duplicate trade_id"):
                load_master_trades(path)

    @staticmethod
    def _manifest(version: str) -> dict[str, object]:
        return {
            "version": version,
            "display_name": version,
            "edition": "Test",
            "parent": None,
            "status": "CANDIDATE",
            "goal": "Test strategy",
            "metrics": {"score": 80},
            "strategy_dna": {"entry": "Rule"},
            "changes": [],
            "lessons": [],
        }

    @staticmethod
    def _trades(version: str) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "trade_id": ["t1", "t2"],
                "strategy_version": [version, version],
                "symbol": ["BTCUSDT", "ETHUSDT"],
                "entry_time": pd.to_datetime(["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"]),
                "exit_time": pd.to_datetime(["2026-01-01T01:00:00Z", "2026-01-02T01:00:00Z"]),
                "net_profit": [10.0, -5.0],
                "result": ["WIN", "LOSS"],
            }
        )


class StrategyDashboardIntegrationTests(unittest.TestCase):
    def test_generate_dashboard_creates_valid_html_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            strategy_dir = root / "strategy_lab" / "strategies" / "v1"
            history_dir = root / "strategy_lab" / "history"
            strategy_dir.mkdir(parents=True)
            history_dir.mkdir(parents=True)

            manifest = StrategyDashboardUnitTests._manifest("v1")
            (strategy_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            StrategyDashboardUnitTests._trades("v1").to_csv(history_dir / "master_trade_history.csv", index=False)

            paths = generate_dashboard(root)
            self.assertTrue(paths.html_output.is_file())
            self.assertTrue(paths.json_output.is_file())
            payload = json.loads(paths.json_output.read_text(encoding="utf-8"))
            self.assertEqual(payload["source"]["master_trade_rows"], 2)
            self.assertEqual(payload["strategies"][0]["calculated_metrics"]["net_profit"], 5.0)
            html_text = paths.html_output.read_text(encoding="utf-8")
            self.assertIn("TCP Strategy Lab Dashboard", html_text)
            self.assertIn("BTCUSDT", html_text)


if __name__ == "__main__":
    unittest.main()
