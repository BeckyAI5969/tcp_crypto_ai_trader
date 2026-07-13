"""One-command Sprint 28 integration runner.

Executes Modules 28.1 through 28.4 in dependency order and writes a
machine-readable final validation report.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Sequence

LOGGER = logging.getLogger(__name__)


class Sprint28RunnerError(RuntimeError):
    """Raised when a Sprint 28 module command fails."""


@dataclass(frozen=True)
class ModuleResult:
    module: str
    command: list[str]
    return_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class Sprint28Paths:
    project_root: Path

    @property
    def validation_output(self) -> Path:
        return self.project_root / "strategy_lab" / "sprint28_validation.json"


MODULE_COMMANDS: tuple[tuple[str, str], ...] = (
    ("28.1", "strategy_lab/database/database_builder.py"),
    ("28.2", "strategy_lab/dashboard/strategy_dashboard.py"),
    ("28.3", "strategy_lab/analyzers/root_cause_summary.py"),
    ("28.4", "strategy_lab/manifest/strategy_manifest.py"),
)

REQUIRED_OUTPUTS: tuple[str, ...] = (
    "strategy_lab/history/master_trade_history.csv",
    "strategy_lab/history/master_trade_validation.json",
    "strategy_lab/dashboard/strategy_dashboard.html",
    "strategy_lab/dashboard/strategy_dashboard.json",
    "strategy_lab/analyzers/root_cause_summary/ROOT_CAUSE_SUMMARY.md",
    "strategy_lab/analyzers/root_cause_summary/root_cause_summary.json",
    "strategy_lab/analyzers/root_cause_summary/root_cause_findings.csv",
    "strategy_lab/manifest/strategy_manifest.json",
    "strategy_lab/manifest/strategy_manifest_validation.json",
)


def _atomic_write_json(path: Path, document: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, newline="\n"
    ) as handle:
        handle.write(rendered)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def _run_command(project_root: Path, module: str, relative_script: str) -> ModuleResult:
    script_path = project_root / relative_script
    if not script_path.is_file():
        raise Sprint28RunnerError(f"Module {module} script not found: {script_path}")

    command = [sys.executable, "-B", str(script_path), "--project-root", str(project_root)]
    LOGGER.info("Running Module %s: %s", module, " ".join(command))
    completed = subprocess.run(
        command,
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    result = ModuleResult(
        module=module,
        command=command,
        return_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    if completed.returncode != 0:
        raise Sprint28RunnerError(
            f"Module {module} failed with exit code {completed.returncode}. "
            f"stdout={completed.stdout!r} stderr={completed.stderr!r}"
        )
    return result


def _validate_outputs(project_root: Path, outputs: Sequence[str] = REQUIRED_OUTPUTS) -> list[str]:
    missing_or_empty: list[str] = []
    for relative in outputs:
        path = project_root / relative
        if not path.is_file() or path.stat().st_size == 0:
            missing_or_empty.append(relative)
    return missing_or_empty


def run_sprint28(project_root: Path) -> dict[str, object]:
    root = project_root.resolve()
    if not (root / "strategy_lab").is_dir():
        raise Sprint28RunnerError(f"strategy_lab directory not found under project root: {root}")

    results: list[ModuleResult] = []
    try:
        for module, relative_script in MODULE_COMMANDS:
            results.append(_run_command(root, module, relative_script))
        invalid_outputs = _validate_outputs(root)
        if invalid_outputs:
            raise Sprint28RunnerError(
                "Required Sprint 28 outputs are missing or empty: " + ", ".join(invalid_outputs)
            )
    except Sprint28RunnerError as exc:
        report: dict[str, object] = {
            "sprint": 28,
            "status": "FAIL",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "project_root": str(root),
            "completed_modules": [result.module for result in results],
            "error": str(exc),
            "module_results": [asdict(result) for result in results],
        }
        _atomic_write_json(Sprint28Paths(root).validation_output, report)
        raise

    report = {
        "sprint": 28,
        "status": "PASS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_root": str(root),
        "completed_modules": [result.module for result in results],
        "required_outputs": list(REQUIRED_OUTPUTS),
        "module_results": [asdict(result) for result in results],
    }
    _atomic_write_json(Sprint28Paths(root).validation_output, report)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run all Sprint 28 Strategy Lab modules")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="TCP Crypto AI Trader repository root",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        report = run_sprint28(args.project_root)
    except Sprint28RunnerError as exc:
        LOGGER.error("Sprint 28 integration failed: %s", exc)
        return 1

    print("Sprint 28 PASS")
    print("Completed modules: " + ", ".join(report["completed_modules"]))
    print(f"Validation report: {Sprint28Paths(args.project_root.resolve()).validation_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
