from __future__ import annotations

import argparse
import json
import logging
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

LOGGER = logging.getLogger("strategy_manifest")

REQUIRED_FIELDS = {
    "version": str,
    "display_name": str,
    "edition": str,
    "parent": str,
    "status": str,
    "goal": str,
    "metrics": dict,
    "strategy_dna": dict,
    "changes": list,
    "lessons": list,
}
ALLOWED_STATUSES = {"DRAFT", "PLANNED", "CANDIDATE", "BENCHMARK", "ARCHIVED", "READY", "REJECTED"}
PERCENT_METRICS = {"win_rate"}
NON_NEGATIVE_METRICS = {"trades", "score", "profit_factor"}


class ManifestValidationError(ValueError):
    """Raised when one or more strategy manifests are invalid."""


@dataclass(frozen=True)
class ManifestPaths:
    project_root: Path

    @property
    def strategies_dir(self) -> Path:
        return self.project_root / "strategy_lab" / "strategies"

    @property
    def output_manifest(self) -> Path:
        return self.project_root / "strategy_lab" / "manifest" / "strategy_manifest.json"

    @property
    def output_validation(self) -> Path:
        return self.project_root / "strategy_lab" / "manifest" / "strategy_manifest_validation.json"

    @property
    def dashboard_json(self) -> Path:
        return self.project_root / "strategy_lab" / "dashboard" / "strategy_dashboard.json"


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestValidationError(f"Required file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(f"Invalid JSON in {path}: {exc}") from exc


def discover_manifest_files(strategies_dir: Path) -> list[Path]:
    if not strategies_dir.is_dir():
        raise ManifestValidationError(f"Strategies directory not found: {strategies_dir}")
    files = sorted(strategies_dir.glob("*/manifest.json"), key=lambda item: item.parent.name)
    if not files:
        raise ManifestValidationError(f"No strategy manifests found under: {strategies_dir}")
    return files


def _validate_text_list(value: Any, field: str, source: Path, errors: list[str]) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        errors.append(f"{source}: '{field}' must be a list of non-empty strings")


def _validate_metrics(metrics: dict[str, Any], source: Path, errors: list[str]) -> None:
    for name, value in metrics.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"{source}: metric '{name}' must be numeric")
            continue
        numeric = float(value)
        if not math.isfinite(numeric):
            errors.append(f"{source}: metric '{name}' must be finite")
        if name in NON_NEGATIVE_METRICS and numeric < 0:
            errors.append(f"{source}: metric '{name}' must not be negative")
        if name in PERCENT_METRICS and not 0 <= numeric <= 100:
            errors.append(f"{source}: metric '{name}' must be between 0 and 100")


def validate_manifest(document: Any, source: Path) -> list[str]:
    errors: list[str] = []
    if not isinstance(document, dict):
        return [f"{source}: root must be a JSON object"]

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in document:
            errors.append(f"{source}: missing required field '{field}'")
        elif not isinstance(document[field], expected_type):
            errors.append(f"{source}: '{field}' must be {expected_type.__name__}")

    if errors:
        return errors

    for field in ("version", "display_name", "status", "goal"):
        if not document[field].strip():
            errors.append(f"{source}: '{field}' must not be empty")

    if document["status"] not in ALLOWED_STATUSES:
        errors.append(f"{source}: unsupported status '{document['status']}'")
    if document["version"] != source.parent.name:
        errors.append(
            f"{source}: version '{document['version']}' does not match directory '{source.parent.name}'"
        )

    _validate_metrics(document["metrics"], source, errors)
    _validate_text_list(document["changes"], "changes", source, errors)
    _validate_text_list(document["lessons"], "lessons", source, errors)

    for key, value in document["strategy_dna"].items():
        if not isinstance(key, str) or not key.strip() or not isinstance(value, str) or not value.strip():
            errors.append(f"{source}: strategy_dna keys and values must be non-empty strings")
            break
    return errors


def _validate_graph(manifests: list[dict[str, Any]], errors: list[str]) -> None:
    by_version = {item["version"]: item for item in manifests}
    if len(by_version) != len(manifests):
        errors.append("Duplicate strategy version detected")
        return

    for item in manifests:
        parent = item["parent"]
        if parent and parent not in by_version:
            errors.append(f"{item['version']}: parent '{parent}' does not exist")
        if parent == item["version"]:
            errors.append(f"{item['version']}: strategy cannot be its own parent")

    for version in by_version:
        seen: set[str] = set()
        cursor = version
        while cursor:
            if cursor in seen:
                errors.append(f"Parent cycle detected from strategy '{version}'")
                break
            seen.add(cursor)
            node = by_version.get(cursor)
            if node is None:
                break
            cursor = node["parent"]


def _topological_order(manifests: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    by_version = {item["version"]: item for item in manifests}
    ordered: list[dict[str, Any]] = []
    visited: set[str] = set()

    def visit(version: str) -> None:
        if version in visited:
            return
        parent = by_version[version]["parent"]
        if parent:
            visit(parent)
        visited.add(version)
        ordered.append(by_version[version])

    for version in sorted(by_version):
        visit(version)
    return ordered


def _dashboard_reconciliation(paths: ManifestPaths, versions: set[str]) -> dict[str, Any]:
    if not paths.dashboard_json.exists():
        return {"available": False, "reason": "strategy_dashboard.json not found"}
    dashboard = _read_json(paths.dashboard_json)
    rows = dashboard.get("strategies") if isinstance(dashboard, dict) else None
    if not isinstance(rows, list):
        raise ManifestValidationError("strategy_dashboard.json has no valid 'strategies' list")
    dashboard_versions = {
        row.get("version") for row in rows if isinstance(row, dict) and isinstance(row.get("version"), str)
    }
    return {
        "available": True,
        "manifest_only_versions": sorted(versions - dashboard_versions),
        "dashboard_only_versions": sorted(dashboard_versions - versions),
        "consistent": versions == dashboard_versions,
    }


def build_strategy_manifest(project_root: Path) -> tuple[Path, Path, dict[str, Any]]:
    paths = ManifestPaths(project_root.resolve())
    files = discover_manifest_files(paths.strategies_dir)
    manifests: list[dict[str, Any]] = []
    errors: list[str] = []

    for source in files:
        document = _read_json(source)
        manifest_errors = validate_manifest(document, source)
        errors.extend(manifest_errors)
        if not manifest_errors:
            manifests.append(document)

    if len(manifests) == len(files):
        _validate_graph(manifests, errors)
    if errors:
        raise ManifestValidationError("\n".join(errors))

    ordered = _topological_order(manifests)
    versions = {item["version"] for item in ordered}
    reconciliation = _dashboard_reconciliation(paths, versions)
    if reconciliation.get("available") and not reconciliation.get("consistent"):
        raise ManifestValidationError(
            "Strategy manifest and dashboard version sets are inconsistent: "
            f"{reconciliation}"
        )

    consolidated = {
        "schema_version": "1.0.0",
        "module": "28.4",
        "strategy_count": len(ordered),
        "root_strategies": [item["version"] for item in ordered if not item["parent"]],
        "strategies": ordered,
    }
    validation = {
        "status": "PASS",
        "module": "28.4",
        "manifest_count": len(ordered),
        "versions": [item["version"] for item in ordered],
        "unique_versions": True,
        "parent_graph_valid": True,
        "dashboard_reconciliation": reconciliation,
        "source_files": [str(path.relative_to(paths.project_root)) for path in files],
    }

    _atomic_write_json(paths.output_manifest, consolidated)
    _atomic_write_json(paths.output_validation, validation)
    LOGGER.info("Strategy manifest built: strategies=%d", len(ordered))
    return paths.output_manifest, paths.output_validation, validation


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and validate the Sprint 28 strategy manifest")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="TCP Crypto AI Trader repository root",
    )
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = _parser().parse_args()
    try:
        output, validation, report = build_strategy_manifest(args.project_root)
    except ManifestValidationError as exc:
        LOGGER.error("Strategy manifest validation failed: %s", exc)
        return 1
    except OSError as exc:
        LOGGER.exception("Strategy manifest write failed: %s", exc)
        return 1
    print(f"Strategy manifest PASS: strategies={report['manifest_count']}")
    print(f"Manifest: {output}")
    print(f"Validation: {validation}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
