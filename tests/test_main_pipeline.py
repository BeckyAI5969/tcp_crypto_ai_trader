"""Integration tests for the TCP Crypto AI Trader main pipeline.

Run from the repository root:

    py -B -m unittest tests.test_main_pipeline -v
"""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from main_pipeline import MainPipeline, PipelineContext  # noqa: E402


class MainPipelineIntegrationTests(unittest.TestCase):

    def setUp(self) -> None:
        self.pipeline = MainPipeline()

    @staticmethod
    def valid_context(**overrides: object) -> PipelineContext:
        values: dict[str, object] = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "confidence": 91.0,
            "account_balance": 1000.0,
            "free_margin": 1000.0,
            "risk_pct": 0.02,
            "entry_price": 60000.0,
            "atr": 400.0,
            "volatility_pct": 0.012,
            "current_margin_usage_pct": 0.10,
            "decision_approved": True,
            "risk_approved": True,
        }
        values.update(overrides)
        return PipelineContext(**values)

    def test_valid_paper_pipeline_completes(self) -> None:
        result = self.pipeline.run(self.valid_context())

        self.assertTrue(result.success)
        self.assertEqual(result.stage, "COMPLETED")
        self.assertIn("execution_plan", result.data)
        self.assertIn("order", result.data)

        execution = (
            result.data.get("execution")
            or result.data.get("paper_trade")
            or result.data.get("testnet_execution")
        )
        self.assertIsNotNone(
            execution,
            "Pipeline result must contain an execution result.",
        )

    def test_invalid_side_is_rejected(self) -> None:
        result = self.pipeline.run(
            self.valid_context(side="HOLD")
        )

        self.assertFalse(result.success)
        self.assertEqual(result.stage, "INPUT_VALIDATION")

    def test_unapproved_ai_decision_stops_pipeline(self) -> None:
        result = self.pipeline.run(
            self.valid_context(decision_approved=False)
        )

        self.assertFalse(result.success)
        self.assertEqual(result.stage, "AI_DECISION")

    def test_failed_risk_validation_stops_pipeline(self) -> None:
        result = self.pipeline.run(
            self.valid_context(risk_approved=False)
        )

        self.assertFalse(result.success)
        self.assertEqual(result.stage, "RISK_VALIDATION")

    def test_low_confidence_is_rejected(self) -> None:
        result = self.pipeline.run(
            self.valid_context(confidence=50.0)
        )

        self.assertFalse(result.success)
        self.assertIn(
            result.stage,
            {"DYNAMIC_LEVERAGE", "EXECUTION_PLAN"},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)