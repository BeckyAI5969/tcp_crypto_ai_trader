"""Generate the Sprint 28 strategy dashboard from validated repository data."""

from __future__ import annotations

import argparse
import html
import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

LOGGER = logging.getLogger(__name__)

REQUIRED_TRADE_COLUMNS = {
    "trade_id",
    "strategy_version",
    "symbol",
    "entry_time",
    "exit_time",
    "net_profit",
    "result",
}
REQUIRED_MANIFEST_FIELDS = {
    "version",
    "display_name",
    "edition",
    "status",
    "goal",
    "metrics",
    "strategy_dna",
    "changes",
    "lessons",
}


class DashboardError(RuntimeError):
    """Raised when dashboard inputs or outputs are invalid."""


@dataclass(frozen=True)
class DashboardPaths:
    """Resolved inputs and outputs for the Strategy Dashboard."""

    project_root: Path
    master_trade_database: Path
    strategies_directory: Path
    html_output: Path
    json_output: Path

    @classmethod
    def from_project_root(cls, project_root: Path) -> "DashboardPaths":
        root = project_root.resolve()
        lab = root / "strategy_lab"
        dashboard = lab / "dashboard"
        return cls(
            project_root=root,
            master_trade_database=lab / "history" / "master_trade_history.csv",
            strategies_directory=lab / "strategies",
            html_output=dashboard / "strategy_dashboard.html",
            json_output=dashboard / "strategy_dashboard.json",
        )


@dataclass(frozen=True)
class StrategyMetrics:
    """Metrics calculated directly from the master trade database."""

    trades: int
    wins: int
    losses: int
    win_rate: float
    gross_profit: float
    gross_loss: float
    profit_factor: float | None
    net_profit: float
    expectancy: float
    max_drawdown: float

    def as_dict(self) -> dict[str, int | float | None]:
        return {
            "trades": self.trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.win_rate,
            "gross_profit": self.gross_profit,
            "gross_loss": self.gross_loss,
            "profit_factor": self.profit_factor,
            "net_profit": self.net_profit,
            "expectancy": self.expectancy,
            "max_drawdown": self.max_drawdown,
        }


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


def _require_mapping(value: Any, *, source: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DashboardError(f"Manifest must contain a JSON object: {source}")
    return value


def load_manifests(strategies_directory: Path) -> list[dict[str, Any]]:
    if not strategies_directory.is_dir():
        raise DashboardError(f"Strategies directory not found: {strategies_directory}")

    manifests: list[dict[str, Any]] = []
    versions: set[str] = set()
    for path in sorted(strategies_directory.glob("*/manifest.json")):
        try:
            manifest = _require_mapping(json.loads(path.read_text(encoding="utf-8")), source=path)
        except json.JSONDecodeError as exc:
            raise DashboardError(f"Invalid manifest JSON: {path}: {exc}") from exc

        missing = sorted(REQUIRED_MANIFEST_FIELDS.difference(manifest))
        if missing:
            raise DashboardError(f"Manifest missing fields {missing}: {path}")

        version = str(manifest["version"]).strip()
        if not version:
            raise DashboardError(f"Manifest version is empty: {path}")
        if version in versions:
            raise DashboardError(f"Duplicate strategy version in manifests: {version}")
        versions.add(version)

        if not isinstance(manifest["metrics"], dict):
            raise DashboardError(f"Manifest metrics must be an object: {path}")
        if not isinstance(manifest["strategy_dna"], dict):
            raise DashboardError(f"Manifest strategy_dna must be an object: {path}")
        if not isinstance(manifest["changes"], list) or not isinstance(manifest["lessons"], list):
            raise DashboardError(f"Manifest changes and lessons must be arrays: {path}")

        manifest["_source_file"] = str(path.relative_to(strategies_directory.parent.parent))
        manifests.append(manifest)

    if not manifests:
        raise DashboardError(f"No strategy manifests found in: {strategies_directory}")
    return manifests


def load_master_trades(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise DashboardError(f"Master trade database not found: {path}")
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError) as exc:
        raise DashboardError(f"Unable to read master trade database: {path}: {exc}") from exc

    missing = sorted(REQUIRED_TRADE_COLUMNS.difference(frame.columns))
    if missing:
        raise DashboardError(f"Master trade database missing columns: {missing}")
    if frame.empty:
        raise DashboardError("Master trade database is empty")
    if frame["trade_id"].duplicated().any():
        raise DashboardError("Master trade database contains duplicate trade_id values")

    frame = frame.copy()
    frame["strategy_version"] = frame["strategy_version"].astype("string").str.strip()
    frame["symbol"] = frame["symbol"].astype("string").str.strip()
    frame["result"] = frame["result"].astype("string").str.strip().str.upper()
    frame["net_profit"] = pd.to_numeric(frame["net_profit"], errors="coerce")
    frame["entry_time"] = pd.to_datetime(frame["entry_time"], errors="coerce", utc=True)
    frame["exit_time"] = pd.to_datetime(frame["exit_time"], errors="coerce", utc=True)

    invalid = frame[
        frame["strategy_version"].isna()
        | frame["symbol"].isna()
        | frame["net_profit"].isna()
        | frame["entry_time"].isna()
        | frame["exit_time"].isna()
        | (frame["exit_time"] < frame["entry_time"])
    ]
    if not invalid.empty:
        identifiers = invalid["trade_id"].astype(str).head(5).tolist()
        raise DashboardError(f"Master trade database contains invalid rows: {identifiers}")
    return frame.sort_values(["strategy_version", "exit_time", "trade_id"], kind="stable")


def _max_drawdown(net_profit: pd.Series) -> float:
    cumulative = net_profit.cumsum()
    initial = pd.Series([0.0], dtype="float64")
    curve = pd.concat([initial, cumulative.reset_index(drop=True)], ignore_index=True)
    drawdown = curve - curve.cummax()
    return float(drawdown.min())


def calculate_metrics(trades: pd.DataFrame) -> StrategyMetrics:
    if trades.empty:
        raise DashboardError("Cannot calculate metrics from an empty trade set")

    profits = trades["net_profit"].astype(float)
    wins = profits[profits > 0]
    losses = profits[profits < 0]
    gross_profit = float(wins.sum())
    gross_loss = float(losses.sum())
    profit_factor = gross_profit / abs(gross_loss) if gross_loss < 0 else None
    trade_count = int(len(trades))

    return StrategyMetrics(
        trades=trade_count,
        wins=int((profits > 0).sum()),
        losses=int((profits < 0).sum()),
        win_rate=float((profits > 0).sum() / trade_count * 100.0),
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=profit_factor,
        net_profit=float(profits.sum()),
        expectancy=float(profits.mean()),
        max_drawdown=_max_drawdown(profits),
    )


def _symbol_metrics(trades: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol, group in trades.groupby("symbol", sort=True):
        metrics = calculate_metrics(group)
        rows.append({"symbol": str(symbol), **metrics.as_dict()})
    return rows


def _metric_difference(reported: Any, calculated: float | int | None) -> float | None:
    if reported is None or calculated is None:
        return None
    try:
        return float(calculated) - float(reported)
    except (TypeError, ValueError):
        return None


def build_dashboard_model(
    manifests: Iterable[dict[str, Any]],
    trades: pd.DataFrame,
) -> dict[str, Any]:
    manifest_list = list(manifests)
    manifest_by_version = {str(item["version"]): item for item in manifest_list}
    trade_versions = set(trades["strategy_version"].dropna().astype(str).unique())
    unknown_versions = sorted(trade_versions.difference(manifest_by_version))
    if unknown_versions:
        raise DashboardError(f"Trade database contains versions without manifests: {unknown_versions}")

    records: list[dict[str, Any]] = []
    for manifest in manifest_list:
        version = str(manifest["version"])
        strategy_trades = trades.loc[trades["strategy_version"] == version]
        calculated = calculate_metrics(strategy_trades) if not strategy_trades.empty else None
        reported_metrics = dict(manifest.get("metrics", {}))
        calculated_dict = calculated.as_dict() if calculated else None
        reconciliation: dict[str, float | None] = {}
        if calculated_dict:
            for name in ("trades", "win_rate", "profit_factor", "net_profit", "expectancy", "max_drawdown"):
                reconciliation[name] = _metric_difference(reported_metrics.get(name), calculated_dict.get(name))

        records.append(
            {
                "version": version,
                "display_name": str(manifest["display_name"]),
                "edition": str(manifest["edition"]),
                "parent": manifest.get("parent") or None,
                "status": str(manifest["status"]),
                "goal": str(manifest["goal"]),
                "created_at_utc": manifest.get("created_at_utc"),
                "manifest_source": manifest.get("_source_file"),
                "reported_metrics": reported_metrics,
                "calculated_metrics": calculated_dict,
                "metric_reconciliation": reconciliation,
                "symbol_metrics": _symbol_metrics(strategy_trades) if calculated else [],
                "strategy_dna": dict(manifest["strategy_dna"]),
                "changes": [str(value) for value in manifest["changes"]],
                "lessons": [str(value) for value in manifest["lessons"]],
            }
        )

    return {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "master_trade_rows": int(len(trades)),
            "strategy_manifest_count": len(manifest_list),
            "trade_versions": sorted(trade_versions),
        },
        "strategies": records,
    }


def _format_number(value: Any, decimals: int = 2) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return "—"


def _stars(score: Any) -> str:
    try:
        count = max(0, min(5, round(float(score) / 20.0)))
    except (TypeError, ValueError):
        count = 0
    return "★" * count + "☆" * (5 - count)


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _render_list(values: list[str], empty_label: str) -> str:
    if not values:
        return f"<li>{_escape(empty_label)}</li>"
    return "".join(f"<li>{_escape(value)}</li>" for value in values)


def render_dashboard_html(model: dict[str, Any]) -> str:
    rows: list[str] = []
    details: list[str] = []
    tree: list[str] = []

    for strategy in model["strategies"]:
        reported = strategy["reported_metrics"]
        calculated = strategy["calculated_metrics"] or {}
        score = reported.get("score")
        data_status = "TRADE DATA" if strategy["calculated_metrics"] else "NO TRADE DATA"

        rows.append(
            "<tr>"
            f"<td>{_escape(strategy['display_name'])}</td>"
            f"<td>{_escape(strategy['edition'])}</td>"
            f"<td>{_escape(strategy['status'])}</td>"
            f"<td>{_escape(data_status)}</td>"
            f"<td>{_format_number(calculated.get('trades'), 0)}</td>"
            f"<td>{_format_number(calculated.get('profit_factor'), 4)}</td>"
            f"<td>{_format_number(calculated.get('win_rate'))}%</td>"
            f"<td>{_format_number(calculated.get('max_drawdown'))}</td>"
            f"<td>{_format_number(calculated.get('net_profit'))}</td>"
            f"<td>{_format_number(score)}</td>"
            f"<td class='stars'>{_stars(score)}</td>"
            "</tr>"
        )
        tree.append(
            "<div class='node'>"
            f"<b>{_escape(strategy['display_name'])}</b>"
            f"<small>{_escape(strategy['goal'])}</small>"
            f"<span>{_escape(strategy['status'])}</span>"
            "</div>"
        )

        dna = "".join(
            f"<tr><th>{_escape(key.replace('_', ' ').title())}</th><td>{_escape(value)}</td></tr>"
            for key, value in strategy["strategy_dna"].items()
        )
        symbols = "".join(
            "<tr>"
            f"<td>{_escape(item['symbol'])}</td>"
            f"<td>{_format_number(item['trades'], 0)}</td>"
            f"<td>{_format_number(item['win_rate'])}%</td>"
            f"<td>{_format_number(item['profit_factor'], 4)}</td>"
            f"<td>{_format_number(item['net_profit'])}</td>"
            f"<td>{_format_number(item['max_drawdown'])}</td>"
            "</tr>"
            for item in strategy["symbol_metrics"]
        ) or "<tr><td colspan='6'>No trade data for this strategy.</td></tr>"

        details.append(
            "<section>"
            f"<h2>{_escape(strategy['display_name'])} — {_escape(strategy['edition'])}</h2>"
            f"<p><b>Status:</b> {_escape(strategy['status'])} | "
            f"<b>Parent:</b> {_escape(strategy['parent'] or 'None')} | "
            f"<b>Goal:</b> {_escape(strategy['goal'])}</p>"
            "<div class='metrics'>"
            f"<div>Trades<b>{_format_number(calculated.get('trades'), 0)}</b></div>"
            f"<div>PF<b>{_format_number(calculated.get('profit_factor'), 4)}</b></div>"
            f"<div>WR<b>{_format_number(calculated.get('win_rate'))}%</b></div>"
            f"<div>Max DD<b>{_format_number(calculated.get('max_drawdown'))}</b></div>"
            f"<div>Net<b>{_format_number(calculated.get('net_profit'))}</b></div>"
            f"<div>Rating<b class='stars'>{_stars(score)}</b></div>"
            "</div>"
            "<div class='grid'>"
            f"<div><h3>Strategy DNA</h3><table>{dna}</table></div>"
            "<div><h3>Changes</h3><ul>"
            f"{_render_list(strategy['changes'], 'None')}</ul>"
            "<h3>Lessons</h3><ul>"
            f"{_render_list(strategy['lessons'], 'Pending')}</ul></div>"
            "</div>"
            "<h3>Actual Performance by Symbol</h3>"
            "<div class='overview'><table><tr><th>Symbol</th><th>Trades</th><th>WR</th>"
            f"<th>PF</th><th>Net</th><th>Max DD</th></tr>{symbols}</table></div>"
            "</section>"
        )

    generated = _escape(model["generated_at_utc"])
    source = model["source"]
    return f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>TCP Strategy Lab Dashboard</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#f4f6f8;color:#18212b;margin:0}}
.wrap{{max-width:1450px;margin:auto;padding:28px}} .hero{{background:#20384d;color:white;padding:25px;border-radius:12px}}
table{{border-collapse:collapse;width:100%;background:white}} th,td{{border:1px solid #dce3e8;padding:8px;text-align:left}}
th{{background:#243447;color:white}} .overview{{overflow:auto}} section{{background:white;border:1px solid #dce3e8;border-radius:12px;padding:20px;margin:20px 0}}
.metrics{{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}} .metrics div{{background:#f6f8fa;padding:12px;border-radius:8px}}
.metrics b{{display:block;font-size:20px;margin-top:4px}} .grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.grid th{{background:#eef2f5;color:#243447;width:170px}} .stars{{color:#a85d00;font-size:18px}}
.tree{{display:flex;gap:10px;overflow:auto;margin:18px 0}} .node{{min-width:180px;background:white;border:2px solid #cbd5e1;border-radius:10px;padding:12px}}
.node small,.node span{{display:block;color:#66727f;margin-top:5px}} .note{{background:#fff7ed;border-left:5px solid #b94700;padding:14px;margin:18px 0}}
.meta{{font-size:13px;color:#52606d;margin-top:10px}} @media(max-width:900px){{.metrics{{grid-template-columns:repeat(2,1fr)}}.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body><main class='wrap'>
<div class='hero'><h1>TCP Strategy Lab Dashboard</h1><p>Validated strategy performance, history, DNA and evolution.</p>
<div class='meta'>Generated: {generated} | Master trades: {source['master_trade_rows']} | Manifests: {source['strategy_manifest_count']}</div></div>
<div class='note'><b>Research Rule:</b> No version is deleted. Every result remains evidence for future learning. Dashboard performance is calculated from the Master Trade Database.</div>
<h2>Evolution</h2><div class='tree'>{''.join(tree)}</div>
<h2>Version Comparison</h2><div class='overview'><table><tr><th>Strategy</th><th>Edition</th><th>Status</th><th>Data</th><th>Trades</th><th>PF</th><th>WR</th><th>DD</th><th>Net</th><th>Score</th><th>Rating</th></tr>{''.join(rows)}</table></div>
<h2>Version Details</h2>{''.join(details)}
</main></body></html>"""


def generate_dashboard(project_root: Path) -> DashboardPaths:
    paths = DashboardPaths.from_project_root(project_root)
    manifests = load_manifests(paths.strategies_directory)
    trades = load_master_trades(paths.master_trade_database)
    model = build_dashboard_model(manifests, trades)
    rendered_json = json.dumps(model, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    rendered_html = render_dashboard_html(model)
    _atomic_write_text(paths.json_output, rendered_json)
    _atomic_write_text(paths.html_output, rendered_html)
    LOGGER.info(
        "Strategy dashboard generated: strategies=%d trades=%d html=%s json=%s",
        len(model["strategies"]),
        len(trades),
        paths.html_output,
        paths.json_output,
    )
    return paths


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate the TCP Strategy Lab dashboard")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Project root containing strategy_lab (default: detected repository root)",
    )
    parser.add_argument("--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        paths = generate_dashboard(args.project_root)
    except DashboardError as exc:
        LOGGER.error("Dashboard generation failed: %s", exc)
        return 1
    except OSError as exc:
        LOGGER.exception("Dashboard output failed: %s", exc)
        return 1

    print(f"Dashboard HTML: {paths.html_output}")
    print(f"Dashboard JSON: {paths.json_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
