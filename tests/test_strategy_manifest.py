from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from strategy_lab.manifest.strategy_manifest import ManifestValidationError, build_strategy_manifest


BASE_MANIFEST = {
    "version": "v1",
    "display_name": "v1",
    "edition": "Test",
    "parent": "",
    "status": "CANDIDATE",
    "goal": "Validate manifest",
    "metrics": {"trades": 1, "win_rate": 100.0, "profit_factor": 2.0},
    "strategy_dna": {"entry": "Rule"},
    "changes": ["Initial"],
    "lessons": [],
}


class StrategyManifestTests(unittest.TestCase):
    def _root(self) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "strategy_lab" / "strategies" / "v1").mkdir(parents=True)
        (root / "strategy_lab" / "manifest").mkdir(parents=True)
        return root

    def _write(self, root: Path, manifest: dict) -> None:
        path = root / "strategy_lab" / "strategies" / manifest["version"] / "manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest), encoding="utf-8")

    def test_builds_consolidated_manifest(self) -> None:
        root = self._root()
        self._write(root, dict(BASE_MANIFEST))
        output, validation, report = build_strategy_manifest(root)
        self.assertTrue(output.exists())
        self.assertTrue(validation.exists())
        self.assertEqual(report["manifest_count"], 1)
        payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["strategies"][0]["version"], "v1")

    def test_rejects_missing_parent(self) -> None:
        root = self._root()
        manifest = dict(BASE_MANIFEST)
        manifest["parent"] = "missing"
        self._write(root, manifest)
        with self.assertRaises(ManifestValidationError):
            build_strategy_manifest(root)

    def test_rejects_invalid_metric(self) -> None:
        root = self._root()
        manifest = dict(BASE_MANIFEST)
        manifest["metrics"] = {"win_rate": 101}
        self._write(root, manifest)
        with self.assertRaises(ManifestValidationError):
            build_strategy_manifest(root)

    def test_rejects_dashboard_version_mismatch(self) -> None:
        root = self._root()
        self._write(root, dict(BASE_MANIFEST))
        dashboard = root / "strategy_lab" / "dashboard"
        dashboard.mkdir(parents=True)
        (dashboard / "strategy_dashboard.json").write_text(
            json.dumps({"strategies": [{"version": "v2"}]}), encoding="utf-8"
        )
        with self.assertRaises(ManifestValidationError):
            build_strategy_manifest(root)


if __name__ == "__main__":
    unittest.main()
