"""TCP Crypto AI Trader — Root Cause Analyzer v1.0

One-command usage from the repository root:

    py -B research\root_cause_analyzer.py

The analyzer compares the v0.1.0 production backtest with the research
benchmark and creates evidence-based reports under:

    research/root_cause_report_v1.0/

It does not modify strategy code or backtest results.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKTEST_REPORT_DIR = PROJECT_ROOT / "reports" / "backtest_v0.1.0"
RESEARCH_DIR = PROJECT_ROOT / "research"
OUTPUT_DIR = RESEARCH_DIR / "root_cause_report_v1.0"


INPUTS = {
    "backtest_summary": BACKTEST_REPORT_DIR / "backtest_summary.csv",
    "benchmark_comparison": BACKTEST_REPORT_DIR / "benchmark_comparison.csv",
    "trade_journal": BACKTEST_REPORT_DIR / "trade_journal.csv",
    "backtest_run": BACKTEST_REPORT_DIR / "backtest_run.json",
    "portfolio_benchmark": RESEARCH_DIR / "portfolio_backtest_report.csv",
    "walk_forward": RESEARCH_DIR / "walk_forward_report.csv",
    "feature_importance": RESEARCH_DIR / "feature_importance.csv",
    "final_trade_analysis": RESEARCH_DIR / "final_trade_analysis.csv",
    "portfolio_trade_log": RESEARCH_DIR / "portfolio_trade_log.csv",
    "optimization_v2_best": RESEARCH_DIR / "optimization_lab_v2_best.csv",
    "optimization_v3_best": RESEARCH_DIR / "optimization_lab_v3_best.csv",
    "optimization_v4_best": RESEARCH_DIR / "optimization_lab_v4_best.csv",
    "optimization_v4_all": RESEARCH_DIR / "optimization_lab_v4.csv",
}


@dataclass(frozen=True)
class RootCause:
    priority: int
    severity: str
    confidence: str
    category: str
    cause: str
    evidence: str
    impact: str
    recommended_action: str


def read_csv(name: str, required: bool = False) -> pd.DataFrame | None:
    path = INPUTS[name]
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Required input not found: {path}")
        return None
    return pd.read_csv(path)


def read_json(name: str) -> dict[str, Any]:
    path = INPUTS[name]
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def safe_number(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def format_number(value: Any, digits: int = 2) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "N/A"
    if isinstance(value, str):
        return value
    return f"{float(value):,.{digits}f}"


def markdown_table(df: pd.DataFrame, columns: list[str] | None = None) -> str:
    if df is None or df.empty:
        return "_No data available._\n"
    view = df.copy()
    if columns:
        existing = [column for column in columns if column in view.columns]
        view = view[existing]
    view = view.fillna("")
    headers = [str(column) for column in view.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for row in view.itertuples(index=False, name=None):
        values = [str(value).replace("|", r"\|") for value in row]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def parse_version(filename_key: str) -> str:
    match = re.search(r"v(\d+)", filename_key)
    return f"v{match.group(1)}" if match else filename_key


def analyze_kpi_gaps(comparison: pd.DataFrame) -> pd.DataFrame:
    output = comparison.copy()

    for metric in ("trades", "win_rate", "net_profit", "profit_factor",
                   "max_drawdown", "expectancy"):
        baseline_col = f"baseline_{metric}"
        current_col = f"v0.1.0_{metric}"
        if baseline_col in output.columns and current_col in output.columns:
            baseline = pd.to_numeric(output[baseline_col], errors="coerce")
            current = pd.to_numeric(output[current_col], errors="coerce")
            output[f"absolute_gap_{metric}"] = current - baseline

            denominator = baseline.abs().replace(0, pd.NA)
            output[f"relative_gap_pct_{metric}"] = (
                (current - baseline) / denominator * 100
            ).round(2)

    selected = [
        "symbol",
        "baseline_trades", "v0.1.0_trades", "absolute_gap_trades",
        "baseline_win_rate", "v0.1.0_win_rate", "absolute_gap_win_rate",
        "baseline_profit_factor", "v0.1.0_profit_factor",
        "absolute_gap_profit_factor",
        "baseline_net_profit", "v0.1.0_net_profit",
        "absolute_gap_net_profit",
        "baseline_max_drawdown", "v0.1.0_max_drawdown",
        "absolute_gap_max_drawdown",
        "baseline_expectancy", "v0.1.0_expectancy",
        "absolute_gap_expectancy",
    ]
    return output[[column for column in selected if column in output.columns]]


def analyze_exits(journal: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    work = journal.copy()
    work["net_profit"] = pd.to_numeric(work["net_profit"], errors="coerce").fillna(0)
    work["is_win"] = work["net_profit"] > 0
    work["holding_hours"] = (
        pd.to_datetime(work["exit_time"], utc=True, errors="coerce")
        - pd.to_datetime(work["entry_time"], utc=True, errors="coerce")
    ).dt.total_seconds() / 3600

    exit_summary = (
        work.groupby("exit_reason", dropna=False)
        .agg(
            trades=("net_profit", "size"),
            wins=("is_win", "sum"),
            win_rate=("is_win", "mean"),
            gross_profit=("net_profit", lambda series: series[series > 0].sum()),
            gross_loss=("net_profit", lambda series: series[series < 0].sum()),
            net_profit=("net_profit", "sum"),
            average_profit=("net_profit", "mean"),
            average_holding_hours=("holding_hours", "mean"),
        )
        .reset_index()
    )
    exit_summary["win_rate"] = (exit_summary["win_rate"] * 100).round(2)
    exit_summary = exit_summary.round(4)

    symbol_exit = (
        work.groupby(["symbol", "exit_reason"], dropna=False)
        .agg(
            trades=("net_profit", "size"),
            wins=("is_win", "sum"),
            net_profit=("net_profit", "sum"),
            average_profit=("net_profit", "mean"),
        )
        .reset_index()
        .round(4)
    )
    return exit_summary, symbol_exit


def analyze_walk_forward(walk: pd.DataFrame | None) -> pd.DataFrame:
    if walk is None or walk.empty:
        return pd.DataFrame()

    output = walk.copy()
    for column in ("profit_factor", "train_profit_factor", "net_profit",
                   "train_net_profit", "win_rate", "train_win_rate"):
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce")

    if {"train_profit_factor", "profit_factor"}.issubset(output.columns):
        output["profit_factor_degradation"] = (
            output["profit_factor"] - output["train_profit_factor"]
        ).round(4)

    if {"train_net_profit", "net_profit"}.issubset(output.columns):
        output["net_profit_degradation"] = (
            output["net_profit"] - output["train_net_profit"]
        ).round(2)

    if {"train_win_rate", "win_rate"}.issubset(output.columns):
        output["win_rate_degradation"] = (
            output["win_rate"] - output["train_win_rate"]
        ).round(2)

    columns = [
        "symbol", "passed", "train_profit_factor", "profit_factor",
        "profit_factor_degradation", "train_net_profit", "net_profit",
        "net_profit_degradation", "train_win_rate", "win_rate",
        "win_rate_degradation", "trades", "max_drawdown", "expectancy",
    ]
    return output[[column for column in columns if column in output.columns]]


def analyze_optimization_evolution(frames: dict[str, pd.DataFrame | None]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for key, frame in frames.items():
        if frame is None or frame.empty or "symbol" not in frame.columns:
            continue

        version = parse_version(key)
        work = frame.copy()
        for metric in ("profit_factor", "net_profit", "win_rate",
                       "max_drawdown", "expectancy"):
            if metric in work.columns:
                work[metric] = pd.to_numeric(work[metric], errors="coerce")

        for symbol, group in work.groupby("symbol"):
            ranking_columns = [
                column for column in ("profit_factor", "net_profit")
                if column in group.columns
            ]
            if not ranking_columns:
                continue

            ranked = group.sort_values(
                ranking_columns,
                ascending=[False] * len(ranking_columns),
            )
            best = ranked.iloc[0]

            rows.append({
                "version": version,
                "symbol": symbol,
                "rows_evaluated": len(group),
                "best_profit_factor": safe_number(best.get("profit_factor")),
                "best_net_profit": safe_number(best.get("net_profit")),
                "best_win_rate": safe_number(best.get("win_rate")),
                "best_max_drawdown": safe_number(best.get("max_drawdown")),
                "best_expectancy": safe_number(best.get("expectancy")),
                "min_score": best.get("min_score", ""),
                "take_profit_pct": best.get("take_profit_pct", ""),
                "stop_loss_pct": best.get("stop_loss_pct", ""),
                "rsi_range": best.get("rsi_range", ""),
                "atr_mode": best.get("atr_mode", ""),
                "volume_multiplier": best.get("volume_multiplier", ""),
                "exit_mode": best.get("exit_mode", ""),
            })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values(["symbol", "version"]).reset_index(drop=True)


def create_root_causes(
    comparison: pd.DataFrame,
    journal: pd.DataFrame,
    exit_summary: pd.DataFrame,
    walk_forward: pd.DataFrame,
    benchmark: pd.DataFrame | None,
    metadata: dict[str, Any],
    final_trade_analysis: pd.DataFrame | None,
) -> list[RootCause]:
    causes: list[RootCause] = []

    total_trades = len(journal)
    stop_row = exit_summary[
        exit_summary["exit_reason"].astype(str).str.upper() == "STOP_LOSS"
    ]
    stop_trades = int(stop_row["trades"].sum()) if not stop_row.empty else 0
    stop_net = safe_number(stop_row["net_profit"].sum()) if not stop_row.empty else 0
    stop_share = stop_trades / total_trades * 100 if total_trades else 0

    tp_row = exit_summary[
        exit_summary["exit_reason"].astype(str).str.upper() == "TAKE_PROFIT"
    ]
    tp_net = safe_number(tp_row["net_profit"].sum()) if not tp_row.empty else 0

    benchmark_tp = None
    benchmark_sl = None
    benchmark_exit = None
    if benchmark is not None and not benchmark.empty:
        if "take_profit_pct" in benchmark.columns:
            benchmark_tp = benchmark["take_profit_pct"].dropna().mode()
            benchmark_tp = benchmark_tp.iloc[0] if not benchmark_tp.empty else None
        if "stop_loss_pct" in benchmark.columns:
            benchmark_sl = benchmark["stop_loss_pct"].dropna().mode()
            benchmark_sl = benchmark_sl.iloc[0] if not benchmark_sl.empty else None
        if "exit_mode" in benchmark.columns:
            benchmark_exit = benchmark["exit_mode"].dropna().mode()
            benchmark_exit = benchmark_exit.iloc[0] if not benchmark_exit.empty else None

    current_exit = metadata.get("exit", "Unknown")
    causes.append(RootCause(
        priority=1,
        severity="CRITICAL",
        confidence="HIGH",
        category="Exit model parity",
        cause=(
            "The benchmark and v0.1.0 backtest do not use the same exit model."
        ),
        evidence=(
            f"Research benchmark records fixed TP={benchmark_tp} and "
            f"SL={benchmark_sl}, exit_mode={benchmark_exit}; the v0.1.0 run "
            f"records '{current_exit}'. STOP_LOSS produced {stop_trades} of "
            f"{total_trades} exits ({stop_share:.1f}%) and net "
            f"{stop_net:,.2f}, while TAKE_PROFIT netted {tp_net:,.2f}."
        ),
        impact=(
            "This directly changes win rate, profit factor, holding period, "
            "trade sequence, drawdown and net profit."
        ),
        recommended_action=(
            "Add a benchmark-parity test mode using the exact research exit "
            "rules (4% TP, -2% SL and the original EMA20 exit implementation). "
            "Keep the current ATR exit as a separate production mode."
        ),
    ))

    failed_count = 0
    total_walk = 0
    mean_test_pf = None
    mean_train_pf = None
    if walk_forward is not None and not walk_forward.empty:
        total_walk = len(walk_forward)
        if "passed" in walk_forward.columns:
            failed_count = int((~walk_forward["passed"].astype(bool)).sum())
        if "profit_factor" in walk_forward.columns:
            mean_test_pf = pd.to_numeric(
                walk_forward["profit_factor"], errors="coerce"
            ).mean()
        if "train_profit_factor" in walk_forward.columns:
            mean_train_pf = pd.to_numeric(
                walk_forward["train_profit_factor"], errors="coerce"
            ).mean()

    causes.append(RootCause(
        priority=2,
        severity="CRITICAL",
        confidence="HIGH" if total_walk else "MEDIUM",
        category="Research robustness / overfitting",
        cause=(
            "The optimized benchmark is not confirmed by walk-forward testing."
        ),
        evidence=(
            f"{failed_count} of {total_walk} walk-forward rows failed. "
            f"Average train PF={format_number(mean_train_pf, 4)}, "
            f"average test PF={format_number(mean_test_pf, 4)}."
            if total_walk
            else "Walk-forward data was not available."
        ),
        impact=(
            "The optimized benchmark can materially overstate performance on "
            "unseen periods. A production replay can therefore be worse even "
            "when its code is correct."
        ),
        recommended_action=(
            "Use walk-forward and out-of-sample results as the primary go/no-go "
            "gate. Do not tune production code merely to recover the optimized "
            "in-sample benchmark."
        ),
    ))

    count_gap = (
        pd.to_numeric(comparison.get("v0.1.0_trades"), errors="coerce")
        - pd.to_numeric(comparison.get("baseline_trades"), errors="coerce")
    )
    total_abs_count_gap = safe_number(count_gap.abs().sum())
    symbols_with_gap = int((count_gap.fillna(0) != 0).sum())

    causes.append(RootCause(
        priority=3,
        severity="HIGH",
        confidence="HIGH",
        category="Entry/filter/timing parity",
        cause=(
            "The production replay does not generate the same trade population "
            "as the benchmark."
        ),
        evidence=(
            f"Trade counts differ for {symbols_with_gap} symbols, with a total "
            f"absolute difference of {total_abs_count_gap:.0f} trades. This "
            "cannot be caused by position sizing alone."
        ),
        impact=(
            "Different entries lead to different market regimes, exits and "
            "winner/loss distributions; KPI comparison is no longer like-for-like."
        ),
        recommended_action=(
            "Create a parity diagnostic that exports every accepted signal "
            "(symbol, candle time, score and each filter result). Compare it "
            "with the original research signal list before changing strategy rules."
        ),
    ))

    metadata_risk = metadata.get("risk_per_trade", "Unknown")
    metadata_fee = metadata.get("taker_fee_rate_per_side", "Unknown")
    metadata_slip = metadata.get("slippage_rate_per_fill", "Unknown")
    causes.append(RootCause(
        priority=4,
        severity="HIGH",
        confidence="HIGH",
        category="Position sizing and cost assumptions",
        cause=(
            "Production v0.1.0 uses dynamic risk-based sizing, leverage, fees "
            "and slippage; the benchmark P&L model is not documented as identical."
        ),
        evidence=(
            f"v0.1.0 metadata: risk_per_trade={metadata_risk}, "
            f"fee_per_side={metadata_fee}, slippage_per_fill={metadata_slip}. "
            "The research benchmark provides TP/SL and KPI values but no "
            "equivalent dynamic sizing audit trail."
        ),
        impact=(
            "This changes net profit and drawdown magnitude. It does not fully "
            "explain the win-rate collapse, but it amplifies monetary differences."
        ),
        recommended_action=(
            "Report results both in R-multiples/percent returns and currency. "
            "For parity testing, use the same fixed notional or exact sizing "
            "function as the original research."
        ),
    ))

    entry_execution = metadata.get("entry_execution", "Unknown")
    intrabar = metadata.get("intrabar_priority", "Unknown")
    causes.append(RootCause(
        priority=5,
        severity="MEDIUM",
        confidence="HIGH",
        category="Execution timing assumptions",
        cause=(
            "Entry and intrabar sequencing assumptions may differ from research."
        ),
        evidence=(
            f"v0.1.0 uses entry_execution='{entry_execution}' and "
            f"intrabar_priority='{intrabar}'. The benchmark report does not "
            "document the same assumptions."
        ),
        impact=(
            "Close-versus-next-open entry and stop-first handling can change "
            "individual outcomes, particularly volatile candles."
        ),
        recommended_action=(
            "Explicitly test both signal-close and next-open execution. Retain "
            "STOP_FIRST as the conservative result when tick order is unavailable."
        ),
    ))

    if final_trade_analysis is not None and not final_trade_analysis.empty:
        rows = len(final_trade_analysis)
        has_symbol = "symbol" in final_trade_analysis.columns
        has_time = {
            "entry_time", "exit_time"
        }.issubset(final_trade_analysis.columns)
        evidence = (
            f"final_trade_analysis contains {rows} rows but "
            f"symbol column={has_symbol}, entry/exit timestamps={has_time}."
        )
    else:
        evidence = "Detailed research trade data was not available."

    causes.append(RootCause(
        priority=6,
        severity="MEDIUM",
        confidence="HIGH",
        category="Trade-level traceability",
        cause=(
            "The available research outputs are insufficient for exact "
            "trade-by-trade matching."
        ),
        evidence=evidence,
        impact=(
            "The analyzer can prove KPI and model-level differences, but cannot "
            "identify the first divergent candle for every symbol."
        ),
        recommended_action=(
            "Modify the original research backtest to export symbol, entry_time, "
            "exit_time, entry reason and exit reason for every trade. Then run "
            "a timestamp-level diff against trade_journal.csv."
        ),
    ))

    return causes


def build_recommendations(causes: list[RootCause]) -> pd.DataFrame:
    rows = []
    for cause in sorted(causes, key=lambda item: item.priority):
        rows.append({
            "sequence": cause.priority,
            "action": cause.recommended_action,
            "reason": cause.cause,
            "expected_result": {
                1: "Separate benchmark parity from production ATR performance.",
                2: "Prevent overfit benchmark from becoming a live-trading target.",
                3: "Explain trade-count differences with candle-level evidence.",
                4: "Make monetary KPI comparison fair and auditable.",
                5: "Quantify execution-model sensitivity.",
                6: "Enable exact trade-by-trade root-cause attribution.",
            }.get(cause.priority, ""),
        })
    return pd.DataFrame(rows)


def build_data_quality() -> pd.DataFrame:
    rows = []
    for name, path in INPUTS.items():
        row = {
            "input": name,
            "path": str(path),
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
            "status": "AVAILABLE" if path.exists() else "MISSING",
        }
        rows.append(row)
    return pd.DataFrame(rows)


def write_report(
    kpi_gaps: pd.DataFrame,
    exit_summary: pd.DataFrame,
    symbol_exit: pd.DataFrame,
    walk_forward: pd.DataFrame,
    feature_importance: pd.DataFrame | None,
    optimization: pd.DataFrame,
    causes: list[RootCause],
    recommendations: pd.DataFrame,
    data_quality: pd.DataFrame,
    metadata: dict[str, Any],
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    root_cause_df = pd.DataFrame([asdict(cause) for cause in causes])
    kpi_gaps.to_csv(OUTPUT_DIR / "kpi_gap_analysis.csv", index=False)
    exit_summary.to_csv(OUTPUT_DIR / "exit_reason_analysis.csv", index=False)
    symbol_exit.to_csv(OUTPUT_DIR / "symbol_exit_analysis.csv", index=False)
    walk_forward.to_csv(OUTPUT_DIR / "walk_forward_analysis.csv", index=False)
    optimization.to_csv(OUTPUT_DIR / "optimization_evolution.csv", index=False)
    root_cause_df.to_csv(OUTPUT_DIR / "root_causes.csv", index=False)
    recommendations.to_csv(OUTPUT_DIR / "improvement_plan.csv", index=False)
    data_quality.to_csv(OUTPUT_DIR / "data_quality.csv", index=False)

    if feature_importance is not None:
        feature_importance.to_csv(
            OUTPUT_DIR / "feature_importance_analysis.csv",
            index=False,
        )

    total_backtest_net = safe_number(
        pd.to_numeric(kpi_gaps.get("v0.1.0_net_profit"), errors="coerce").sum()
    )
    total_benchmark_net = safe_number(
        pd.to_numeric(kpi_gaps.get("baseline_net_profit"), errors="coerce").sum()
    )

    report: list[str] = []
    report.append("# TCP Crypto AI Trader — Root Cause Report v1.0\n\n")
    report.append(
        f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n"
    )

    report.append("## Executive conclusion\n\n")
    report.append(
        "The first v0.1.0 backtest is operational, but it is **not a "
        "like-for-like reproduction** of the research benchmark. The largest "
        "confirmed cause is the exit-model mismatch: the benchmark uses fixed "
        "4% TP / -2% SL with EMA20 exit, while v0.1.0 applies ATR-based exits "
        "and dynamic risk sizing. In addition, every available walk-forward "
        "test failed, showing that the optimized benchmark itself does not "
        "generalize reliably. Therefore, the current loss must not be attributed "
        "to one coding defect or used to tune the strategy blindly.\n\n"
    )
    report.append(
        f"Combined benchmark net profit: **{total_benchmark_net:,.2f}**  \n"
        f"Combined v0.1.0 net profit: **{total_backtest_net:,.2f}**\n\n"
    )

    report.append("## Ranked root causes\n\n")
    for cause in sorted(causes, key=lambda item: item.priority):
        report.append(
            f"### {cause.priority}. {cause.category} "
            f"({cause.severity}, confidence {cause.confidence})\n\n"
            f"**Cause:** {cause.cause}\n\n"
            f"**Evidence:** {cause.evidence}\n\n"
            f"**Impact:** {cause.impact}\n\n"
            f"**Recommended improvement:** {cause.recommended_action}\n\n"
        )

    report.append("## KPI gap by symbol\n\n")
    report.append(markdown_table(kpi_gaps))

    report.append("## Exit-reason evidence\n\n")
    report.append(markdown_table(exit_summary))

    report.append("## Walk-forward evidence\n\n")
    report.append(markdown_table(walk_forward))

    if feature_importance is not None and not feature_importance.empty:
        report.append("## Feature-importance evidence\n\n")
        top_features = feature_importance.sort_values(
            "edge_score", ascending=False
        ).head(10)
        report.append(markdown_table(top_features))

    report.append("## Improvement plan\n\n")
    report.append(markdown_table(recommendations))

    report.append("## Decision gate\n\n")
    report.append(
        "- **Do not proceed to real trading.**\n"
        "- Do not optimize v0.1.0 to force agreement with the in-sample benchmark.\n"
        "- First create a benchmark-parity mode and a signal audit.\n"
        "- Then evaluate production v0.1.0 separately using walk-forward and "
        "out-of-sample data.\n"
        "- Proceed to Testnet execution only when out-of-sample expectancy and "
        "profit factor are positive and operational checks pass.\n"
    )

    (OUTPUT_DIR / "ROOT_CAUSE_REPORT_v1.0.md").write_text(
        "".join(report),
        encoding="utf-8",
    )

    run_metadata = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "analyzer_version": "1.0",
        "project_backtest_metadata": metadata,
        "output_directory": str(OUTPUT_DIR),
        "root_cause_count": len(causes),
        "critical_count": sum(
            cause.severity == "CRITICAL" for cause in causes
        ),
        "high_count": sum(
            cause.severity == "HIGH" for cause in causes
        ),
    }
    (OUTPUT_DIR / "root_cause_run.json").write_text(
        json.dumps(run_metadata, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    print("=" * 72)
    print("TCP CRYPTO AI TRADER — ROOT CAUSE ANALYZER v1.0")
    print("=" * 72)

    summary = read_csv("backtest_summary", required=True)
    comparison = read_csv("benchmark_comparison", required=True)
    journal = read_csv("trade_journal", required=True)
    metadata = read_json("backtest_run")

    benchmark = read_csv("portfolio_benchmark")
    walk = read_csv("walk_forward")
    feature = read_csv("feature_importance")
    final_trade = read_csv("final_trade_analysis")

    optimization_frames = {
        "optimization_v2_best": read_csv("optimization_v2_best"),
        "optimization_v3_best": read_csv("optimization_v3_best"),
        "optimization_v4_best": read_csv("optimization_v4_best"),
        "optimization_v4_all": read_csv("optimization_v4_all"),
    }

    print("Analyzing KPI gaps...")
    kpi_gaps = analyze_kpi_gaps(comparison)

    print("Analyzing exit behavior...")
    exit_summary, symbol_exit = analyze_exits(journal)

    print("Analyzing walk-forward robustness...")
    walk_forward = analyze_walk_forward(walk)

    print("Analyzing optimization evolution...")
    optimization = analyze_optimization_evolution(optimization_frames)

    print("Ranking root causes...")
    causes = create_root_causes(
        comparison=comparison,
        journal=journal,
        exit_summary=exit_summary,
        walk_forward=walk_forward,
        benchmark=benchmark,
        metadata=metadata,
        final_trade_analysis=final_trade,
    )
    recommendations = build_recommendations(causes)
    data_quality = build_data_quality()

    print("Writing report...")
    write_report(
        kpi_gaps=kpi_gaps,
        exit_summary=exit_summary,
        symbol_exit=symbol_exit,
        walk_forward=walk_forward,
        feature_importance=feature,
        optimization=optimization,
        causes=causes,
        recommendations=recommendations,
        data_quality=data_quality,
        metadata=metadata,
    )

    print("")
    print("ROOT CAUSE ANALYSIS COMPLETED")
    print(f"Report: {OUTPUT_DIR / 'ROOT_CAUSE_REPORT_v1.0.md'}")
    print(f"Details: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
