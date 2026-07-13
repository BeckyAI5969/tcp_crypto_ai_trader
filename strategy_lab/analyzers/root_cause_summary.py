"""Generate Sprint 28 root-cause summaries from validated trade history.

One-command usage from the repository root::

    py -B strategy_lab\analyzers\root_cause_summary.py

The module reports evidence-backed loss concentrations and metric gaps. It does
not infer hidden market or implementation causes that are absent from the data.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

LOGGER = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "trade_id",
    "strategy_version",
    "symbol",
    "entry_time",
    "exit_time",
    "exit_reason",
    "net_profit",
}


class RootCauseSummaryError(RuntimeError):
    """Raised when root-cause inputs or outputs are invalid."""


@dataclass(frozen=True)
class RootCausePaths:
    """Resolved repository paths used by the analyzer."""

    project_root: Path
    master_trade_database: Path
    strategies_directory: Path
    output_directory: Path
    markdown_output: Path
    json_output: Path
    csv_output: Path

    @classmethod
    def from_project_root(cls, project_root: Path) -> "RootCausePaths":
        root = project_root.resolve()
        lab = root / "strategy_lab"
        output = lab / "analyzers" / "root_cause_summary"
        return cls(
            project_root=root,
            master_trade_database=lab / "history" / "master_trade_history.csv",
            strategies_directory=lab / "strategies",
            output_directory=output,
            markdown_output=output / "ROOT_CAUSE_SUMMARY.md",
            json_output=output / "root_cause_summary.json",
            csv_output=output / "root_cause_findings.csv",
        )


@dataclass(frozen=True)
class Finding:
    """Evidence-backed concentration observed in the trade database."""

    priority: int
    strategy_version: str
    category: str
    dimension: str
    value: str
    trades: int
    losses: int
    net_profit: float
    loss_contribution_pct: float
    confidence: str
    interpretation: str
    evidence_scope: str


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _atomic_write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            frame.to_csv(handle, index=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def load_trades(path: Path) -> pd.DataFrame:
    """Load and validate the master trade database."""

    if not path.is_file():
        raise RootCauseSummaryError(f"Master trade database not found: {path}")
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError) as exc:
        raise RootCauseSummaryError(f"Unable to read master trade database: {path}: {exc}") from exc

    missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        raise RootCauseSummaryError(f"Master trade database missing columns: {missing}")
    if frame.empty:
        raise RootCauseSummaryError("Master trade database is empty")
    if frame["trade_id"].duplicated().any():
        raise RootCauseSummaryError("Master trade database contains duplicate trade_id values")

    work = frame.copy()
    for column in ("strategy_version", "symbol", "exit_reason"):
        work[column] = work[column].astype("string").str.strip()
    work["net_profit"] = pd.to_numeric(work["net_profit"], errors="coerce")
    work["entry_time"] = pd.to_datetime(work["entry_time"], errors="coerce", utc=True)
    work["exit_time"] = pd.to_datetime(work["exit_time"], errors="coerce", utc=True)

    invalid = work[
        work["strategy_version"].isna()
        | work["symbol"].isna()
        | work["exit_reason"].isna()
        | work["net_profit"].isna()
        | work["entry_time"].isna()
        | work["exit_time"].isna()
        | (work["exit_time"] < work["entry_time"])
    ]
    if not invalid.empty:
        identifiers = invalid["trade_id"].astype(str).head(5).tolist()
        raise RootCauseSummaryError(f"Master trade database contains invalid rows: {identifiers}")

    work["is_loss"] = work["net_profit"] < 0
    return work.sort_values(["strategy_version", "exit_time", "trade_id"], kind="stable")


def load_manifest_metrics(strategies_directory: Path) -> dict[str, dict[str, Any]]:
    """Load version metrics used only for explicit reconciliation."""

    if not strategies_directory.is_dir():
        raise RootCauseSummaryError(f"Strategies directory not found: {strategies_directory}")

    output: dict[str, dict[str, Any]] = {}
    for path in sorted(strategies_directory.glob("*/manifest.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RootCauseSummaryError(f"Invalid manifest JSON: {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise RootCauseSummaryError(f"Manifest must contain a JSON object: {path}")
        version = str(value.get("version", "")).strip()
        metrics = value.get("metrics")
        if not version or not isinstance(metrics, dict):
            raise RootCauseSummaryError(f"Manifest version or metrics invalid: {path}")
        if version in output:
            raise RootCauseSummaryError(f"Duplicate strategy manifest version: {version}")
        output[version] = metrics

    if not output:
        raise RootCauseSummaryError(f"No strategy manifests found in: {strategies_directory}")
    return output


def _loss_contribution(net_profit: float, total_negative_profit: float) -> float:
    if net_profit >= 0 or total_negative_profit >= 0:
        return 0.0
    return abs(net_profit) / abs(total_negative_profit) * 100.0


def _group_findings(
    version: str,
    trades: pd.DataFrame,
    dimension: str,
    category: str,
    total_negative_profit: float,
) -> list[Finding]:
    grouped = (
        trades.groupby(dimension, dropna=False)
        .agg(
            trades=("trade_id", "size"),
            losses=("is_loss", "sum"),
            net_profit=("net_profit", "sum"),
        )
        .reset_index()
    )
    grouped = grouped[grouped["net_profit"] < 0].copy()
    grouped["loss_contribution_pct"] = grouped["net_profit"].map(
        lambda value: _loss_contribution(float(value), total_negative_profit)
    )
    grouped = grouped.sort_values(
        ["loss_contribution_pct", "losses", "trades"],
        ascending=[False, False, False],
        kind="stable",
    )

    findings: list[Finding] = []
    for row in grouped.itertuples(index=False):
        contribution = float(row.loss_contribution_pct)
        confidence = "HIGH" if int(row.trades) >= 30 else "MEDIUM" if int(row.trades) >= 10 else "LOW"
        value = str(getattr(row, dimension))
        findings.append(
            Finding(
                priority=0,
                strategy_version=version,
                category=category,
                dimension=dimension,
                value=value,
                trades=int(row.trades),
                losses=int(row.losses),
                net_profit=float(row.net_profit),
                loss_contribution_pct=contribution,
                confidence=confidence,
                interpretation=(
                    f"Observed negative P&L concentration for {dimension}={value}. "
                    "This is a measured association, not proof of an underlying causal mechanism."
                ),
                evidence_scope="master_trade_history.csv",
            )
        )
    return findings


def calculate_version_metrics(trades: pd.DataFrame) -> dict[str, float | int | None]:
    profits = trades["net_profit"].astype(float)
    gross_profit = float(profits[profits > 0].sum())
    gross_loss = float(profits[profits < 0].sum())
    count = int(len(profits))
    cumulative = profits.cumsum()
    curve = pd.concat([pd.Series([0.0]), cumulative.reset_index(drop=True)], ignore_index=True)
    return {
        "trades": count,
        "win_rate": float((profits > 0).sum() / count * 100.0),
        "profit_factor": gross_profit / abs(gross_loss) if gross_loss < 0 else None,
        "net_profit": float(profits.sum()),
        "expectancy": float(profits.mean()),
        "max_drawdown": float((curve - curve.cummax()).min()),
    }


def build_summary(
    trades: pd.DataFrame,
    manifest_metrics: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[Finding]]:
    """Build summary model and ranked evidence-backed findings."""

    versions = sorted(trades["strategy_version"].astype(str).unique())
    unknown = sorted(set(versions).difference(manifest_metrics))
    if unknown:
        raise RootCauseSummaryError(f"Trade versions have no strategy manifest: {unknown}")

    all_findings: list[Finding] = []
    version_summaries: list[dict[str, Any]] = []
    for version in versions:
        subset = trades[trades["strategy_version"] == version].copy()
        calculated = calculate_version_metrics(subset)
        total_negative_profit = float(subset.loc[subset["net_profit"] < 0, "net_profit"].sum())

        findings = []
        findings.extend(_group_findings(version, subset, "exit_reason", "EXIT_REASON", total_negative_profit))
        findings.extend(_group_findings(version, subset, "symbol", "SYMBOL", total_negative_profit))
        all_findings.extend(findings)

        reported = manifest_metrics[version]
        reconciliation: dict[str, dict[str, float | int | None]] = {}
        for metric in ("trades", "win_rate", "profit_factor", "net_profit", "expectancy", "max_drawdown"):
            reported_value = reported.get(metric)
            calculated_value = calculated.get(metric)
            difference: float | None = None
            if reported_value is not None and calculated_value is not None:
                try:
                    difference = float(calculated_value) - float(reported_value)
                except (TypeError, ValueError):
                    difference = None
            reconciliation[metric] = {
                "reported": reported_value,
                "calculated": calculated_value,
                "difference": difference,
            }

        version_summaries.append(
            {
                "strategy_version": version,
                "calculated_metrics": calculated,
                "manifest_reconciliation": reconciliation,
                "negative_pnl_total": total_negative_profit,
                "finding_count": len(findings),
            }
        )

    ranked = sorted(
        all_findings,
        key=lambda item: (
            -item.loss_contribution_pct,
            -item.losses,
            item.strategy_version,
            item.category,
            item.value,
        ),
    )
    ranked = [Finding(**{**asdict(item), "priority": index}) for index, item in enumerate(ranked, start=1)]

    model = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "strategy_lab/history/master_trade_history.csv",
        "methodology": {
            "scope": "Descriptive loss concentration and manifest reconciliation",
            "causality_limit": (
                "Findings identify measured associations in recorded trades. They do not prove hidden "
                "market, execution, or implementation causes without additional evidence."
            ),
            "confidence_rule": "HIGH >=30 trades; MEDIUM 10-29 trades; LOW <10 trades",
        },
        "trade_count": int(len(trades)),
        "strategy_versions": versions,
        "versions": version_summaries,
        "findings": [asdict(item) for item in ranked],
    }
    return model, ranked


def _format_value(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:,.4f}"
    return str(value)


def render_markdown(model: dict[str, Any]) -> str:
    lines = [
        "# Sprint 28 Root Cause Summary",
        "",
        f"Generated: `{model['generated_at_utc']}`",
        f"Trade records: **{model['trade_count']:,}**",
        f"Strategy versions: **{', '.join(model['strategy_versions'])}**",
        "",
        "## Methodology and limitation",
        "",
        model["methodology"]["causality_limit"],
        "",
        "## Version metrics",
        "",
        "| Version | Trades | Win Rate | Profit Factor | Net Profit | Expectancy | Max Drawdown |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for version in model["versions"]:
        metrics = version["calculated_metrics"]
        lines.append(
            "| {version} | {trades} | {win_rate:.4f}% | {pf} | {net:.4f} | {exp:.4f} | {dd:.4f} |".format(
                version=version["strategy_version"],
                trades=metrics["trades"],
                win_rate=metrics["win_rate"],
                pf=_format_value(metrics["profit_factor"]),
                net=metrics["net_profit"],
                exp=metrics["expectancy"],
                dd=metrics["max_drawdown"],
            )
        )

    lines.extend(
        [
            "",
            "## Ranked observed loss concentrations",
            "",
            "| Priority | Version | Category | Value | Trades | Losses | Net Profit | Loss Contribution | Confidence |",
            "|---:|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    findings = model["findings"]
    if not findings:
        lines.append("| - | - | - | No negative concentration found | 0 | 0 | 0 | 0% | - |")
    else:
        for item in findings:
            lines.append(
                "| {priority} | {strategy_version} | {category} | {value} | {trades} | {losses} | "
                "{net_profit:.4f} | {loss_contribution_pct:.2f}% | {confidence} |".format(**item)
            )

    lines.extend(
        [
            "",
            "## Interpretation rule",
            "",
            "Each finding is a descriptive association from the master trade database. "
            "A finding must not be treated as proof that the named symbol or exit rule caused the loss.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(paths: RootCausePaths, model: dict[str, Any], findings: Iterable[Finding]) -> None:
    serialized = json.dumps(model, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    _atomic_write_text(paths.json_output, serialized)
    _atomic_write_text(paths.markdown_output, render_markdown(model))
    frame = pd.DataFrame([asdict(item) for item in findings])
    if frame.empty:
        frame = pd.DataFrame(columns=list(Finding.__dataclass_fields__))
    _atomic_write_csv(paths.csv_output, frame)


def run(project_root: Path) -> dict[str, Any]:
    paths = RootCausePaths.from_project_root(project_root)
    trades = load_trades(paths.master_trade_database)
    manifests = load_manifest_metrics(paths.strategies_directory)
    model, findings = build_summary(trades, manifests)
    write_outputs(paths, model, findings)
    LOGGER.info(
        "Root cause summary generated: trades=%d versions=%d findings=%d output=%s",
        model["trade_count"],
        len(model["strategy_versions"]),
        len(model["findings"]),
        paths.output_directory,
    )
    return model


def _parse_args() -> argparse.Namespace:
    default_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=default_root)
    parser.add_argument("--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        model = run(args.project_root)
    except RootCauseSummaryError as exc:
        LOGGER.error("Root cause summary failed: %s", exc)
        return 2
    except (OSError, ValueError, TypeError) as exc:
        LOGGER.exception("Unexpected root cause summary failure: %s", exc)
        return 3

    print(f"Root cause summary PASS: trades={model['trade_count']} findings={len(model['findings'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
