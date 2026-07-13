
"""TCP Crypto AI Trader — Trade Intelligence Analyzer v1.0

One-command usage from the repository root:

    py -B research\trade_intelligence_analyzer.py

The script creates one combined standalone HTML report:

    research/TRADE_INTELLIGENCE_REPORT_v1.0.html

It analyzes:
- Why winning trades won
- Why losing trades lost
- Indicator suitability
- AI score usefulness
- Market-regime effects
- Exit strategy effects
- Fees and holding-time effects
- Evidence-based improvement priorities

It never modifies the strategy or backtest results.
"""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports" / "backtest_v0.1.0"
RESEARCH_DIR = PROJECT_ROOT / "research"
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_FILE = RESEARCH_DIR / "TRADE_INTELLIGENCE_REPORT_v1.0.html"

TRADE_JOURNAL = REPORTS_DIR / "trade_journal.csv"
BACKTEST_SUMMARY = REPORTS_DIR / "backtest_summary.csv"
BENCHMARK = REPORTS_DIR / "benchmark_comparison.csv"
BACKTEST_RUN = REPORTS_DIR / "backtest_run.json"

DATASET_CANDIDATES = [
    DATA_DIR / "market_dataset.csv",
    DATA_DIR / "market_dataset.xlsx",
    DATA_DIR / "market_dataset.xls",
]

RESEARCH_FILES = {
    "walk_forward": RESEARCH_DIR / "walk_forward_report.csv",
    "feature_importance": RESEARCH_DIR / "feature_importance.csv",
    "final_trade_analysis": RESEARCH_DIR / "final_trade_analysis.csv",
    "optimization_v4": RESEARCH_DIR / "optimization_lab_v4.csv",
    "portfolio_benchmark": RESEARCH_DIR / "portfolio_backtest_report.csv",
}


def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")


def read_optional_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def find_dataset() -> Path:
    for path in DATASET_CANDIDATES:
        if path.exists():
            return path
    expected = "\n".join(str(path) for path in DATASET_CANDIDATES)
    raise FileNotFoundError(
        "Market dataset not found. Expected one of:\n" + expected
    )


def load_market_dataset(path: Path) -> pd.DataFrame:
    columns = [
        "symbol", "timeframe", "open_time", "open", "high", "low", "close",
        "volume", "EMA20", "EMA50", "EMA200", "RSI14", "MACD",
        "MACD_SIGNAL", "MACD_HIST", "ATR14", "VOLUME_MA20", "atr_pct",
        "bb_width_pct", "ema20_gt_ema50", "ema50_gt_ema200",
        "price_gt_ema200", "macd_gt_signal", "macd_hist_positive",
        "volume_gt_ma20",
    ]

    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, usecols=lambda name: name in columns)
    else:
        df = pd.read_excel(path, usecols=lambda name: name in columns)

    required = {"symbol", "open_time", "close", "EMA20", "EMA50", "EMA200",
                "RSI14", "MACD", "MACD_SIGNAL", "MACD_HIST", "ATR14",
                "volume", "VOLUME_MA20", "atr_pct"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Market dataset missing columns: {missing}")

    df["symbol"] = df["symbol"].astype(str).str.upper()
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True, errors="coerce")
    df = df.dropna(subset=["open_time", "symbol"])
    return df.sort_values(["symbol", "open_time"])


def add_entry_features(trades: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    trades = trades.copy()
    trades["symbol"] = trades["symbol"].astype(str).str.upper()
    trades["entry_time"] = pd.to_datetime(
        trades["entry_time"], utc=True, errors="coerce"
    )
    trades["exit_time"] = pd.to_datetime(
        trades["exit_time"], utc=True, errors="coerce"
    )

    market = market.copy()
    selected = [
        "symbol", "open_time", "close", "EMA20", "EMA50", "EMA200", "RSI14",
        "MACD", "MACD_SIGNAL", "MACD_HIST", "ATR14", "volume",
        "VOLUME_MA20", "atr_pct", "bb_width_pct",
    ]
    selected = [column for column in selected if column in market.columns]

    merged = trades.merge(
        market[selected],
        left_on=["symbol", "entry_time"],
        right_on=["symbol", "open_time"],
        how="left",
    )

    # If exact timestamp is missing, use nearest previous candle within 15 minutes.
    missing = merged["RSI14"].isna()
    if missing.any():
        repaired = []
        for symbol, group in trades[missing].groupby("symbol"):
            source = market[market["symbol"] == symbol][selected].sort_values("open_time")
            target = group.sort_values("entry_time")
            nearest = pd.merge_asof(
                target,
                source,
                left_on="entry_time",
                right_on="open_time",
                by="symbol",
                direction="backward",
                tolerance=pd.Timedelta("15min"),
            )
            repaired.append(nearest)
        if repaired:
            repair_df = pd.concat(repaired, ignore_index=True)
            for column in selected:
                if column in {"symbol", "open_time"}:
                    continue
                mapping = repair_df.set_index(
                    ["symbol", "entry_time"]
                )[column]
                keys = list(zip(merged.loc[missing, "symbol"],
                                merged.loc[missing, "entry_time"]))
                merged.loc[missing, column] = [mapping.get(key, np.nan) for key in keys]

    merged["is_win"] = pd.to_numeric(
        merged["net_profit"], errors="coerce"
    ).fillna(0) > 0
    merged["holding_hours"] = (
        merged["exit_time"] - merged["entry_time"]
    ).dt.total_seconds() / 3600
    merged["fee_total"] = (
        pd.to_numeric(merged["entry_fee"], errors="coerce").fillna(0)
        + pd.to_numeric(merged["exit_fee"], errors="coerce").fillna(0)
    )
    merged["gross_profit"] = pd.to_numeric(
        merged["gross_profit"], errors="coerce"
    ).fillna(0)
    merged["net_profit"] = pd.to_numeric(
        merged["net_profit"], errors="coerce"
    ).fillna(0)

    merged["volume_ratio"] = (
        pd.to_numeric(merged["volume"], errors="coerce")
        / pd.to_numeric(merged["VOLUME_MA20"], errors="coerce").replace(0, np.nan)
    )
    merged["ema_gap_pct"] = (
        (pd.to_numeric(merged["EMA20"], errors="coerce")
         - pd.to_numeric(merged["EMA50"], errors="coerce"))
        / pd.to_numeric(merged["close"], errors="coerce").replace(0, np.nan)
        * 100
    )
    merged["price_vs_ema200_pct"] = (
        (pd.to_numeric(merged["close"], errors="coerce")
         - pd.to_numeric(merged["EMA200"], errors="coerce"))
        / pd.to_numeric(merged["EMA200"], errors="coerce").replace(0, np.nan)
        * 100
    )
    merged["macd_strength"] = (
        pd.to_numeric(merged["MACD_HIST"], errors="coerce")
        / pd.to_numeric(merged["close"], errors="coerce").replace(0, np.nan)
        * 100
    )

    merged["trend_regime"] = np.select(
        [
            (merged["EMA20"] > merged["EMA50"])
            & (merged["EMA50"] > merged["EMA200"])
            & (merged["close"] > merged["EMA20"]),
            (merged["EMA20"] > merged["EMA50"])
            & (merged["EMA50"] > merged["EMA200"]),
            merged["close"] < merged["EMA200"],
        ],
        ["STRONG_UPTREND", "UPTREND_WEAK", "BEARISH"],
        default="SIDEWAY",
    )

    merged["volatility_regime"] = pd.cut(
        merged["atr_pct"],
        bins=[-np.inf, 0.35, 0.60, 1.00, np.inf],
        labels=["LOW", "NORMAL", "HIGH", "EXTREME"],
    ).astype(str)

    merged["rsi_zone"] = pd.cut(
        merged["RSI14"],
        bins=[-np.inf, 45, 55, 65, 75, np.inf],
        labels=["<45", "45-55", "55-65", "65-75", ">75"],
    ).astype(str)

    merged["volume_zone"] = pd.cut(
        merged["volume_ratio"],
        bins=[-np.inf, 1.0, 1.15, 1.50, np.inf],
        labels=["BELOW_AVG", "1.00-1.15x", "1.15-1.50x", ">1.50x"],
    ).astype(str)

    return merged


def aggregate_group(df: pd.DataFrame, column: str) -> pd.DataFrame:
    work = df.dropna(subset=[column]).copy()
    if work.empty:
        return pd.DataFrame()

    result = (
        work.groupby(column, dropna=False)
        .agg(
            trades=("net_profit", "size"),
            wins=("is_win", "sum"),
            win_rate=("is_win", "mean"),
            net_profit=("net_profit", "sum"),
            average_trade=("net_profit", "mean"),
            gross_profit=("net_profit", lambda values: values[values > 0].sum()),
            gross_loss=("net_profit", lambda values: values[values < 0].sum()),
            average_hold_hours=("holding_hours", "mean"),
        )
        .reset_index()
    )
    result["win_rate"] = (result["win_rate"] * 100).round(2)
    result["profit_factor"] = np.where(
        result["gross_loss"] < 0,
        result["gross_profit"] / result["gross_loss"].abs(),
        np.where(result["gross_profit"] > 0, np.inf, 0),
    )
    return result.round(4).sort_values("net_profit", ascending=False)


def winner_loser_comparison(df: pd.DataFrame) -> pd.DataFrame:
    metrics = {
        "RSI14": "RSI",
        "atr_pct": "ATR %",
        "volume_ratio": "Volume Ratio",
        "ema_gap_pct": "EMA20-EMA50 Gap %",
        "price_vs_ema200_pct": "Price vs EMA200 %",
        "macd_strength": "MACD Histogram %",
        "holding_hours": "Holding Hours",
        "fee_total": "Fees",
        "ai_score": "AI Score",
    }
    rows = []
    for column, label in metrics.items():
        if column not in df.columns:
            continue
        winners = pd.to_numeric(
            df.loc[df["is_win"], column], errors="coerce"
        ).dropna()
        losers = pd.to_numeric(
            df.loc[~df["is_win"], column], errors="coerce"
        ).dropna()
        if winners.empty and losers.empty:
            continue
        rows.append({
            "metric": label,
            "winner_mean": winners.mean() if not winners.empty else np.nan,
            "loser_mean": losers.mean() if not losers.empty else np.nan,
            "difference": (
                winners.mean() - losers.mean()
                if not winners.empty and not losers.empty else np.nan
            ),
            "winner_median": winners.median() if not winners.empty else np.nan,
            "loser_median": losers.median() if not losers.empty else np.nan,
        })
    return pd.DataFrame(rows).round(4)


def ai_score_analysis(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    score = pd.to_numeric(df["ai_score"], errors="coerce").dropna()
    if score.empty:
        return pd.DataFrame(), "No AI score data was available."

    unique_scores = score.nunique()
    score_range = float(score.max() - score.min())
    analysis = aggregate_group(df.assign(
        ai_score_band=pd.cut(
            pd.to_numeric(df["ai_score"], errors="coerce"),
            bins=[-np.inf, 80, 85, 90, 95, np.inf],
            labels=["<=80", "80-85", "85-90", "90-95", ">95"],
        ).astype(str)
    ), "ai_score_band")

    if unique_scores <= 2 or score_range < 5:
        conclusion = (
            f"AI Score has weak discriminatory power in this backtest: "
            f"only {unique_scores} unique score value(s), range {score_range:.2f}. "
            "A score that is nearly constant cannot separate high-quality entries "
            "from low-quality entries."
        )
    else:
        band_pf = pd.to_numeric(analysis["profit_factor"], errors="coerce")
        conclusion = (
            "AI Score shows some variation. Use the band table to check whether "
            "higher scores consistently improve win rate and profit factor."
            if band_pf.notna().any()
            else "AI Score could not be calibrated from the available rows."
        )
    return analysis, conclusion


def derive_findings(df: pd.DataFrame, grouped: dict[str, pd.DataFrame],
                    ai_conclusion: str,
                    walk_forward: pd.DataFrame) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []

    exit_table = grouped["exit_reason"]
    if not exit_table.empty:
        stop = exit_table[
            exit_table["exit_reason"].astype(str).str.upper() == "STOP_LOSS"
        ]
        if not stop.empty:
            row = stop.iloc[0]
            share = row["trades"] / len(df) * 100
            findings.append({
                "priority": "1",
                "severity": "CRITICAL",
                "topic": "Exit strategy",
                "finding": (
                    f"STOP_LOSS accounts for {share:.1f}% of all trades and "
                    f"contributes net {row['net_profit']:,.2f}."
                ),
                "meaning": (
                    "The current ATR stop/target structure is the strongest direct "
                    "source of losses. Many entries do not develop far enough before "
                    "the stop is reached."
                ),
                "action": (
                    "Test exit variants separately: current ATR exit, benchmark "
                    "4% TP/-2% SL, and ATR stop with earlier profit protection. "
                    "Do not change entry rules at the same time."
                ),
            })

    trend = grouped["trend_regime"]
    if not trend.empty:
        best = trend.iloc[0]
        worst = trend.iloc[-1]
        findings.append({
            "priority": "2",
            "severity": "HIGH",
            "topic": "Market regime",
            "finding": (
                f"Best regime: {best['trend_regime']} "
                f"(WR {best['win_rate']:.2f}%, PF {best['profit_factor']:.2f}); "
                f"worst: {worst['trend_regime']} "
                f"(WR {worst['win_rate']:.2f}%, PF {worst['profit_factor']:.2f})."
            ),
            "meaning": (
                "The same BUY logic behaves differently across trend regimes. "
                "Long-only entries taken during weak or non-trending conditions "
                "create avoidable false signals."
            ),
            "action": (
                "Add a market-regime gate and initially permit new BUY trades only "
                "in the regimes with positive expectancy. Re-backtest before use."
            ),
        })

    vol = grouped["volatility_regime"]
    if not vol.empty:
        best = vol.iloc[0]
        worst = vol.iloc[-1]
        findings.append({
            "priority": "3",
            "severity": "HIGH",
            "topic": "Volatility filter",
            "finding": (
                f"Best volatility regime: {best['volatility_regime']} "
                f"(net {best['net_profit']:,.2f}); worst: "
                f"{worst['volatility_regime']} "
                f"(net {worst['net_profit']:,.2f})."
            ),
            "meaning": (
                "ATR is not only a position-sizing input; it also identifies market "
                "conditions where the strategy performs poorly."
            ),
            "action": (
                "Reject or reduce size in volatility regimes with negative "
                "expectancy. Validate threshold stability per symbol."
            ),
        })

    findings.append({
        "priority": "4",
        "severity": "HIGH",
        "topic": "AI decision calibration",
        "finding": ai_conclusion,
        "meaning": (
            "An AI score that does not rank trade quality cannot improve selection, "
            "even when the pipeline labels the trade as approved."
        ),
        "action": (
            "Recalibrate the decision score using features that separate winners "
            "from losers. Require monotonic improvement across score bands before "
            "using confidence to increase leverage."
        ),
    })

    if not walk_forward.empty and "passed" in walk_forward.columns:
        failed = int((~walk_forward["passed"].astype(bool)).sum())
        findings.append({
            "priority": "5",
            "severity": "CRITICAL",
            "topic": "Overfitting / generalization",
            "finding": (
                f"{failed} of {len(walk_forward)} walk-forward evaluations failed."
            ),
            "meaning": (
                "The attractive optimized benchmark is not stable on unseen data. "
                "Trying to force the production strategy to reproduce it can create "
                "more overfitting."
            ),
            "action": (
                "Use walk-forward and out-of-sample expectancy as the primary gate. "
                "Reject parameter changes that only improve the optimization sample."
            ),
        })

    fee_drag = df["fee_total"].sum()
    gross_abs = df["gross_profit"].abs().sum()
    ratio = fee_drag / gross_abs * 100 if gross_abs else 0
    findings.append({
        "priority": "6",
        "severity": "MEDIUM",
        "topic": "Trading costs",
        "finding": (
            f"Total fees are {fee_drag:,.2f}, equal to {ratio:.1f}% of absolute "
            "gross P&L."
        ),
        "meaning": (
            "Costs are not the main cause of the low win rate, but they materially "
            "worsen marginal trades and frequent re-entry."
        ),
        "action": (
            "Avoid low-edge trades, add cooldown where evidence supports it, and "
            "compare maker/limit execution assumptions separately."
        ),
    })

    return findings


def html_table(df: pd.DataFrame, max_rows: int = 100) -> str:
    if df is None or df.empty:
        return "<p class='muted'>No data available.</p>"
    view = df.head(max_rows).copy()
    for column in view.select_dtypes(include=[np.number]).columns:
        view[column] = view[column].map(
            lambda value: "" if pd.isna(value) else f"{value:,.4f}".rstrip("0").rstrip(".")
        )
    return view.to_html(index=False, escape=True, classes="data-table")


def bar_chart(df: pd.DataFrame, label_col: str, value_col: str,
              title: str, positive_good: bool = True) -> str:
    if df.empty or label_col not in df.columns or value_col not in df.columns:
        return ""
    values = pd.to_numeric(df[value_col], errors="coerce").fillna(0)
    max_abs = max(values.abs().max(), 1e-9)
    rows = []
    for label, value in zip(df[label_col].astype(str), values):
        width = min(100, abs(value) / max_abs * 100)
        color_class = "good" if (value >= 0) == positive_good else "bad"
        rows.append(
            f"<div class='bar-row'><div class='bar-label'>{escape(label)}</div>"
            f"<div class='bar-track'><div class='bar {color_class}' "
            f"style='width:{width:.1f}%'></div></div>"
            f"<div class='bar-value'>{value:,.2f}</div></div>"
        )
    return f"<div class='chart'><h3>{escape(title)}</h3>{''.join(rows)}</div>"


def build_html(summary: pd.DataFrame, benchmark: pd.DataFrame,
               trades: pd.DataFrame, comparison: pd.DataFrame,
               grouped: dict[str, pd.DataFrame],
               win_loss: pd.DataFrame, ai_table: pd.DataFrame,
               ai_conclusion: str, findings: list[dict[str, str]],
               feature_importance: pd.DataFrame,
               walk_forward: pd.DataFrame,
               final_trade_analysis: pd.DataFrame,
               metadata: dict[str, Any],
               dataset_path: Path) -> str:

    total_trades = len(trades)
    wins = int(trades["is_win"].sum())
    losses = total_trades - wins
    net = trades["net_profit"].sum()
    win_rate = wins / total_trades * 100 if total_trades else 0
    gross_win = trades.loc[trades["net_profit"] > 0, "net_profit"].sum()
    gross_loss = trades.loc[trades["net_profit"] < 0, "net_profit"].sum()
    pf = gross_win / abs(gross_loss) if gross_loss < 0 else np.inf
    fees = trades["fee_total"].sum()

    cards = [
        ("Trades", f"{total_trades:,}"),
        ("Win Rate", f"{win_rate:.2f}%"),
        ("Net Profit", f"{net:,.2f}"),
        ("Profit Factor", f"{pf:.3f}"),
        ("Total Fees", f"{fees:,.2f}"),
        ("Matched Entry Data", f"{trades['RSI14'].notna().mean()*100:.1f}%"),
    ]
    cards_html = "".join(
        f"<div class='card'><div class='card-title'>{escape(title)}</div>"
        f"<div class='card-value'>{escape(value)}</div></div>"
        for title, value in cards
    )

    findings_html = "".join(
        f"<div class='finding {item['severity'].lower()}'>"
        f"<div class='finding-head'>Priority {escape(item['priority'])} — "
        f"{escape(item['topic'])} <span>{escape(item['severity'])}</span></div>"
        f"<p><b>Evidence:</b> {escape(item['finding'])}</p>"
        f"<p><b>Interpretation:</b> {escape(item['meaning'])}</p>"
        f"<p><b>Recommended test:</b> {escape(item['action'])}</p></div>"
        for item in findings
    )

    symbol_chart = bar_chart(
        grouped["symbol"], "symbol", "net_profit",
        "Net Profit by Symbol"
    )
    exit_chart = bar_chart(
        grouped["exit_reason"], "exit_reason", "net_profit",
        "Net Profit by Exit Reason"
    )
    regime_chart = bar_chart(
        grouped["trend_regime"], "trend_regime", "net_profit",
        "Net Profit by Market Regime"
    )

    generated = datetime.now(timezone.utc).isoformat()

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>TCP Trade Intelligence Report v1.0</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f4f6f8;color:#18212b;}}
.container{{max-width:1400px;margin:auto;padding:28px;}}
h1{{margin-bottom:6px}} h2{{margin-top:34px;border-bottom:2px solid #d9e0e6;padding-bottom:8px}}
.meta,.muted{{color:#66727f;font-size:13px}}
.cards{{display:grid;grid-template-columns:repeat(6,minmax(140px,1fr));gap:12px;margin:20px 0}}
.card{{background:white;border:1px solid #dce3e8;border-radius:10px;padding:16px;box-shadow:0 1px 3px #00000010}}
.card-title{{font-size:12px;color:#66727f;text-transform:uppercase}} .card-value{{font-size:25px;font-weight:700;margin-top:5px}}
.finding{{background:white;border-left:6px solid #6b7280;border-radius:8px;padding:16px;margin:14px 0;box-shadow:0 1px 3px #00000010}}
.finding.critical{{border-color:#b91c1c}} .finding.high{{border-color:#d97706}} .finding.medium{{border-color:#2563eb}}
.finding-head{{font-weight:700;font-size:17px}} .finding-head span{{float:right;font-size:12px;padding:4px 8px;background:#eef2f5;border-radius:12px}}
.data-table{{border-collapse:collapse;width:100%;background:white;font-size:12px;overflow:auto;display:block}}
.data-table th,.data-table td{{border:1px solid #dce3e8;padding:7px 9px;white-space:nowrap}}
.data-table th{{background:#243447;color:white;position:sticky;top:0}}
.chart{{background:white;border:1px solid #dce3e8;border-radius:10px;padding:16px;margin:16px 0}}
.bar-row{{display:grid;grid-template-columns:150px 1fr 100px;gap:10px;align-items:center;margin:9px 0}}
.bar-track{{height:16px;background:#e8edf1;border-radius:8px;overflow:hidden}}
.bar{{height:100%}} .bar.good{{background:#15803d}} .bar.bad{{background:#b91c1c}}
.bar-value{{text-align:right;font-variant-numeric:tabular-nums}}
.note{{background:#fff7ed;border-left:5px solid #ea580c;padding:14px;border-radius:6px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
code{{background:#eef2f5;padding:2px 5px;border-radius:4px}}
@media(max-width:900px){{.cards{{grid-template-columns:repeat(2,1fr)}}.grid2{{grid-template-columns:1fr}}}}
</style>
</head>
<body><div class="container">
<h1>TCP Crypto AI Trader — Trade Intelligence Report v1.0</h1>
<div class="meta">Generated: {escape(generated)}<br>
Dataset: {escape(str(dataset_path))}<br>
Backtest version: {escape(str(metadata.get("project_version","v0.1.0")))}</div>

<div class="cards">{cards_html}</div>

<div class="note"><b>Important:</b> This report identifies patterns and proposes
tests. It cannot guarantee that any adjustment will create a winning strategy.
Every change must be re-tested on walk-forward and unseen data before Testnet
or real trading.</div>

<h2>Executive Findings and Improvement Priorities</h2>
{findings_html}

<h2>Performance Overview</h2>
<div class="grid2">{symbol_chart}{exit_chart}</div>
{regime_chart}

<h2>Backtest Summary</h2>
{html_table(summary)}

<h2>Benchmark Comparison</h2>
{html_table(comparison)}

<h2>Why Trades Won or Lost — Indicator Comparison</h2>
<p class="muted">Average and median indicator conditions at entry for winning versus losing trades.</p>
{html_table(win_loss)}

<h2>Market Regime Analysis</h2>
<h3>Trend Regime</h3>{html_table(grouped["trend_regime"])}
<h3>Volatility Regime</h3>{html_table(grouped["volatility_regime"])}
<h3>RSI Zone</h3>{html_table(grouped["rsi_zone"])}
<h3>Volume Zone</h3>{html_table(grouped["volume_zone"])}

<h2>AI Decision Analysis</h2>
<p>{escape(ai_conclusion)}</p>
{html_table(ai_table)}

<h2>Exit Strategy Analysis</h2>
{html_table(grouped["exit_reason"])}

<h2>Per-Symbol Analysis</h2>
{html_table(grouped["symbol"])}

<h2>Walk-Forward Robustness</h2>
{html_table(walk_forward)}

<h2>Research Feature Importance</h2>
{html_table(feature_importance.sort_values("edge_score", ascending=False) if not feature_importance.empty and "edge_score" in feature_importance.columns else feature_importance)}

<h2>Original Research Trade Diagnostics</h2>
{html_table(final_trade_analysis.head(100))}

<h2>Recommended Controlled Experiments</h2>
<ol>
<li><b>Exit-only test:</b> keep all entries unchanged and compare ATR exits versus benchmark 4% TP/-2% SL and EMA20 exit.</li>
<li><b>Market-regime gate test:</b> permit entries only in regimes with positive expectancy in this report.</li>
<li><b>AI-score calibration test:</b> ensure higher score bands produce monotonically higher profit factor before linking score to leverage.</li>
<li><b>Volatility filter test:</b> reject the worst ATR regime and compare trade count, PF and drawdown.</li>
<li><b>Cost sensitivity test:</b> rerun with maker/taker assumptions separately.</li>
<li><b>Walk-forward gate:</b> accept a change only when out-of-sample expectancy and PF remain positive.</li>
</ol>

<h2>Decision</h2>
<p><b>Current recommendation:</b> do not proceed to real trading. Use this report
to run one controlled change at a time. The first priority is exit-model testing,
followed by market-regime filtering and AI-score calibration.</p>
</div></body></html>"""


def main() -> None:
    print("=" * 72)
    print("TCP CRYPTO AI TRADER — TRADE INTELLIGENCE ANALYZER v1.0")
    print("=" * 72)

    require_file(TRADE_JOURNAL)
    require_file(BACKTEST_SUMMARY)
    require_file(BENCHMARK)

    dataset_path = find_dataset()

    print("Loading backtest reports...")
    trades = pd.read_csv(TRADE_JOURNAL)
    summary = pd.read_csv(BACKTEST_SUMMARY)
    benchmark = pd.read_csv(BENCHMARK)
    metadata = (
        json.loads(BACKTEST_RUN.read_text(encoding="utf-8"))
        if BACKTEST_RUN.exists() else {}
    )

    print("Loading market dataset and matching entry conditions...")
    market = load_market_dataset(dataset_path)
    trades = add_entry_features(trades, market)

    print("Analyzing winners, losers, indicators and market regimes...")
    grouped = {
        "symbol": aggregate_group(trades, "symbol"),
        "exit_reason": aggregate_group(trades, "exit_reason"),
        "trend_regime": aggregate_group(trades, "trend_regime"),
        "volatility_regime": aggregate_group(trades, "volatility_regime"),
        "rsi_zone": aggregate_group(trades, "rsi_zone"),
        "volume_zone": aggregate_group(trades, "volume_zone"),
    }
    win_loss = winner_loser_comparison(trades)
    ai_table, ai_conclusion = ai_score_analysis(trades)

    walk_forward = read_optional_csv(RESEARCH_FILES["walk_forward"])
    feature_importance = read_optional_csv(RESEARCH_FILES["feature_importance"])
    final_trade_analysis = read_optional_csv(
        RESEARCH_FILES["final_trade_analysis"]
    )

    findings = derive_findings(
        trades, grouped, ai_conclusion, walk_forward
    )

    print("Writing one combined HTML report...")
    html = build_html(
        summary=summary,
        benchmark=benchmark,
        trades=trades,
        comparison=benchmark,
        grouped=grouped,
        win_loss=win_loss,
        ai_table=ai_table,
        ai_conclusion=ai_conclusion,
        findings=findings,
        feature_importance=feature_importance,
        walk_forward=walk_forward,
        final_trade_analysis=final_trade_analysis,
        metadata=metadata,
        dataset_path=dataset_path,
    )

    OUTPUT_FILE.write_text(html, encoding="utf-8")

    print("")
    print("TRADE INTELLIGENCE ANALYSIS COMPLETED")
    print(f"Open this report: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
