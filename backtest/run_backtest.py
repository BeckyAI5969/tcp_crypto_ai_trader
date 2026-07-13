r"""One-command candle replay for TCP Crypto AI Trader v0.1.0.

Run from the repository root:

    py -B backtest\run_backtest.py

Dataset location:
    data\market_dataset.csv
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
REPORT_DIR = PROJECT_ROOT / "reports" / "backtest_v0.1.0"
DATASET_CANDIDATES = [
    PROJECT_ROOT / "data" / "market_dataset.csv",
    PROJECT_ROOT / "data" / "market_dataset.xlsx",
    PROJECT_ROOT / "data" / "market_dataset.xls",
]


def find_dataset_path() -> Path:
    for candidate in DATASET_CANDIDATES:
        if candidate.exists():
            return candidate
    expected = "\n".join(f"- {path}" for path in DATASET_CANDIDATES)
    raise FileNotFoundError(
        "Dataset not found. Expected one of:\n" + expected
    )


DATASET_PATH = find_dataset_path()

# src must be first so src/config.py is never shadowed by backtest settings.
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(1, str(Path(__file__).resolve().parent))

from main_pipeline import MainPipeline, PipelineContext  # noqa: E402
from backtest_settings import (  # noqa: E402
    BENCHMARK,
    INITIAL_BALANCE,
    INTRABAR_PRIORITY,
    LOOKBACK_DAYS,
    RISK_PER_TRADE,
    SLIPPAGE_RATE,
    SYMBOL_RULES,
    TAKER_FEE_RATE,
    TIMEFRAME,
)


FUTURE_COLUMNS = {
    "future_return_4",
    "future_return_8",
    "future_return_16",
    "future_return_32",
    "label_16",
}


@dataclass
class Position:
    symbol: str
    entry_time: str
    entry_price: float
    quantity: float
    leverage: int
    stop_loss: float
    take_profit: float
    entry_fee: float
    ai_score: float
    balance_before: float


def calculate_ai_score(df: pd.DataFrame) -> pd.Series:
    """Reproduce the Weighted AI SignalEngine score from current-candle data."""
    score = pd.Series(0.0, index=df.index)
    score += (df["EMA20"] > df["EMA50"]).astype(float) * 35.0
    score += ((df["RSI14"] > 45) & (df["RSI14"] < 65)).astype(float) * 20.0
    score += (df["MACD"] > 0).astype(float) * 25.0

    # SignalEngine used an always-valid volume fallback when its historical
    # source did not expose the exact mixed-case column it checked.
    score += 10.0
    score += (df["ATR14"] > 0).astype(float) * 10.0
    return score


def load_data() -> pd.DataFrame:
    suffix = DATASET_PATH.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(DATASET_PATH)
    elif suffix in {".xlsx", ".xls"}:
        try:
            df = pd.read_excel(DATASET_PATH)
        except ImportError as exc:
            raise RuntimeError(
                "Excel support requires openpyxl. Install it once with: "
                "py -m pip install openpyxl"
            ) from exc
    else:
        raise ValueError(
            f"Unsupported dataset format: {DATASET_PATH.suffix}"
        )

    required = {
        "symbol", "timeframe", "open_time", "open", "high", "low", "close",
        "volume", "EMA20", "EMA50", "EMA200", "RSI14", "MACD",
        "MACD_SIGNAL", "MACD_HIST", "ATR14", "VOLUME_MA20", "atr_pct",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    df["symbol"] = df["symbol"].astype(str).str.upper()
    df["timeframe"] = df["timeframe"].astype(str)
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True, errors="raise")

    df = df[
        df["symbol"].isin(SYMBOL_RULES)
        & (df["timeframe"] == TIMEFRAME)
    ].copy()

    if df.empty:
        raise ValueError("No matching 15m rows were found for the configured symbols.")

    df = df.sort_values(["symbol", "open_time"]).drop_duplicates(
        ["symbol", "open_time"]
    )

    groups = []
    for symbol, group in df.groupby("symbol", sort=False):
        group = group.copy().sort_values("open_time")
        cutoff = group["open_time"].max() - pd.Timedelta(days=LOOKBACK_DAYS)
        group = group[group["open_time"] >= cutoff].copy()

        group["ATR_MA20"] = group["ATR14"].rolling(20).mean()
        group["ATR_P40"] = group["ATR14"].rolling(200).quantile(0.40)
        group["AI_SCORE"] = calculate_ai_score(group)
        group["Signal"] = "WAIT"
        group.loc[group["AI_SCORE"] >= 80.0, "Signal"] = "BUY"
        group.loc[group["AI_SCORE"] <= 20.0, "Signal"] = "SELL"
        groups.append(group)

    return pd.concat(groups, ignore_index=True)


def disable_console_logs() -> None:
    for name in ("tcp.pipeline", "tcp.trade", "tcp.risk", "tcp.error"):
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            if isinstance(handler, logging.StreamHandler) and not isinstance(
                handler, logging.FileHandler
            ):
                logger.removeHandler(handler)


def entry_allowed(
    group: pd.DataFrame,
    i: int,
    rule: dict[str, Any],
) -> bool:
    row = group.iloc[i]

    if str(row["Signal"]) != "BUY":
        return False
    if float(row["AI_SCORE"]) < float(rule["min_score"]):
        return False
    if not (rule["rsi_low"] <= float(row["RSI14"]) <= rule["rsi_high"]):
        return False
    if not (float(row["EMA50"]) > float(row["EMA200"])):
        return False

    if rule["ema_confirm"]:
        if i < 1:
            return False
        previous = group.iloc[i - 1]
        if not (
            float(row["close"]) > float(row["EMA20"])
            and float(previous["close"]) > float(previous["EMA20"])
        ):
            return False

    if rule["atr_mode"] == "sma20":
        threshold = row["ATR_MA20"]
    else:
        threshold = row["ATR_P40"]

    if pd.isna(threshold) or float(row["ATR14"]) <= float(threshold):
        return False

    if float(row["volume"]) <= (
        float(row["VOLUME_MA20"]) * float(rule["volume_multiplier"])
    ):
        return False

    return True


def check_exit(
    row: pd.Series,
    position: Position,
    exit_mode: str,
) -> tuple[str, float] | None:
    low = float(row["low"])
    high = float(row["high"])
    close = float(row["close"])

    sl_hit = low <= position.stop_loss
    tp_hit = high >= position.take_profit

    if sl_hit and tp_hit:
        if INTRABAR_PRIORITY == "STOP_FIRST":
            return "STOP_LOSS", position.stop_loss
        return "TAKE_PROFIT", position.take_profit
    if sl_hit:
        return "STOP_LOSS", position.stop_loss
    if tp_hit:
        return "TAKE_PROFIT", position.take_profit

    profit_pct = (close - position.entry_price) / position.entry_price
    if (
        exit_mode == "ema20_exit"
        and close < float(row["EMA20"])
        and profit_pct > 0
    ):
        return "EMA20_EXIT", close

    return None


def summarize(
    symbol: str,
    trades: list[dict[str, Any]],
    final_balance: float,
    max_drawdown: float,
) -> dict[str, Any]:
    wins = [trade for trade in trades if trade["net_profit"] > 0]
    losses = [trade for trade in trades if trade["net_profit"] < 0]
    gross_profit = sum(trade["net_profit"] for trade in wins)
    gross_loss = sum(trade["net_profit"] for trade in losses)
    net_profit = final_balance - INITIAL_BALANCE
    profit_factor = (
        gross_profit / abs(gross_loss)
        if gross_loss < 0
        else float("inf") if gross_profit > 0 else 0.0
    )

    return {
        "symbol": symbol,
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 2) if trades else 0.0,
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "net_profit": round(net_profit, 2),
        "profit_factor": round(profit_factor, 4)
        if profit_factor != float("inf") else "Infinity",
        "max_drawdown": round(max_drawdown, 2),
        "expectancy": round(net_profit / len(trades), 2) if trades else 0.0,
        "initial_balance": INITIAL_BALANCE,
        "final_balance": round(final_balance, 2),
        "return_pct": round(net_profit / INITIAL_BALANCE * 100, 2),
    }


def replay_symbol(
    symbol: str,
    group: pd.DataFrame,
    pipeline: MainPipeline,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    rule = SYMBOL_RULES[symbol]
    balance = INITIAL_BALANCE
    peak_equity = INITIAL_BALANCE
    max_drawdown = 0.0
    position: Position | None = None
    trades: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []

    group = group.reset_index(drop=True)

    for i in range(len(group)):
        row = group.iloc[i]
        timestamp = row["open_time"].isoformat()
        close = float(row["close"])

        if position is not None:
            exit_event = check_exit(row, position, rule["exit_mode"])
            if exit_event is not None:
                exit_reason, raw_exit_price = exit_event
                exit_price = raw_exit_price * (1.0 - SLIPPAGE_RATE)
                gross_profit = (
                    exit_price - position.entry_price
                ) * position.quantity
                exit_fee = exit_price * position.quantity * TAKER_FEE_RATE
                net_profit = gross_profit - position.entry_fee - exit_fee
                balance += net_profit

                trades.append({
                    "symbol": symbol,
                    "entry_time": position.entry_time,
                    "exit_time": timestamp,
                    "entry_price": round(position.entry_price, 8),
                    "exit_price": round(exit_price, 8),
                    "quantity": round(position.quantity, 8),
                    "leverage": position.leverage,
                    "stop_loss": round(position.stop_loss, 8),
                    "take_profit": round(position.take_profit, 8),
                    "ai_score": position.ai_score,
                    "exit_reason": exit_reason,
                    "gross_profit": round(gross_profit, 8),
                    "entry_fee": round(position.entry_fee, 8),
                    "exit_fee": round(exit_fee, 8),
                    "net_profit": round(net_profit, 8),
                    "balance_after": round(balance, 8),
                })
                position = None

        if position is None and entry_allowed(group, i, rule):
            raw_entry_price = close
            entry_price = raw_entry_price * (1.0 + SLIPPAGE_RATE)
            ai_score = float(row["AI_SCORE"])

            result = pipeline.run(PipelineContext(
                symbol=symbol,
                side="BUY",
                confidence=ai_score,
                account_balance=balance,
                free_margin=balance,
                risk_pct=RISK_PER_TRADE,
                entry_price=entry_price,
                atr=float(row["ATR14"]),
                volatility_pct=max(0.0, float(row["atr_pct"]) / 100.0),
                current_margin_usage_pct=0.0,
                decision_approved=True,
                risk_approved=True,
            ))

            if result.success:
                order = result.data["order"]
                actual_entry = float(order["entry_price"])
                quantity = float(order["quantity"])
                entry_fee = actual_entry * quantity * TAKER_FEE_RATE

                position = Position(
                    symbol=symbol,
                    entry_time=timestamp,
                    entry_price=actual_entry,
                    quantity=quantity,
                    leverage=int(order["leverage"]),
                    stop_loss=float(order["stop_loss"]),
                    take_profit=float(order["take_profit"]),
                    entry_fee=entry_fee,
                    ai_score=ai_score,
                    balance_before=balance,
                )

        unrealized = 0.0
        if position is not None:
            unrealized = (
                (close - position.entry_price) * position.quantity
                - position.entry_fee
            )

        equity = balance + unrealized
        peak_equity = max(peak_equity, equity)
        drawdown = equity - peak_equity
        max_drawdown = min(max_drawdown, drawdown)

        equity_rows.append({
            "symbol": symbol,
            "open_time": timestamp,
            "balance": round(balance, 8),
            "equity": round(equity, 8),
            "drawdown": round(drawdown, 8),
        })

    # Close an open trade at the final candle so the report is complete.
    if position is not None:
        row = group.iloc[-1]
        exit_price = float(row["close"]) * (1.0 - SLIPPAGE_RATE)
        gross_profit = (exit_price - position.entry_price) * position.quantity
        exit_fee = exit_price * position.quantity * TAKER_FEE_RATE
        net_profit = gross_profit - position.entry_fee - exit_fee
        balance += net_profit
        trades.append({
            "symbol": symbol,
            "entry_time": position.entry_time,
            "exit_time": row["open_time"].isoformat(),
            "entry_price": round(position.entry_price, 8),
            "exit_price": round(exit_price, 8),
            "quantity": round(position.quantity, 8),
            "leverage": position.leverage,
            "stop_loss": round(position.stop_loss, 8),
            "take_profit": round(position.take_profit, 8),
            "ai_score": position.ai_score,
            "exit_reason": "END_OF_DATA",
            "gross_profit": round(gross_profit, 8),
            "entry_fee": round(position.entry_fee, 8),
            "exit_fee": round(exit_fee, 8),
            "net_profit": round(net_profit, 8),
            "balance_after": round(balance, 8),
        })

    return (
        summarize(symbol, trades, balance, max_drawdown),
        trades,
        equity_rows,
    )


def comparison_table(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    metrics = (
        "trades", "wins", "losses", "win_rate", "gross_profit",
        "gross_loss", "net_profit", "profit_factor",
        "max_drawdown", "expectancy",
    )

    for result in summary.to_dict("records"):
        symbol = result["symbol"]
        baseline = BENCHMARK[symbol]
        row: dict[str, Any] = {"symbol": symbol}
        for metric in metrics:
            old = baseline[metric]
            new = result[metric]
            row[f"baseline_{metric}"] = old
            row[f"v0.1.0_{metric}"] = new
            if isinstance(old, (int, float)) and isinstance(new, (int, float)):
                row[f"difference_{metric}"] = round(new - old, 4)
            else:
                row[f"difference_{metric}"] = ""
        rows.append(row)

    return pd.DataFrame(rows)


def main() -> None:
    print("=" * 72)
    print("TCP CRYPTO AI TRADER v0.1.0 - ONE COMMAND BACKTEST")
    print("=" * 72)
    print(f"Dataset : {DATASET_PATH}")
    print(f"Period  : latest {LOOKBACK_DAYS} days per symbol")
    print(f"Mode    : PAPER pipeline, {TIMEFRAME} candles")
    print("Loading data...")

    data = load_data()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    pipeline = MainPipeline()
    disable_console_logs()

    summaries: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    equity: list[dict[str, Any]] = []

    for symbol in SYMBOL_RULES:
        group = data[data["symbol"] == symbol].copy()
        if group.empty:
            print(f"{symbol}: no data - skipped")
            continue

        print(f"{symbol}: replaying {len(group):,} candles...")
        summary, symbol_trades, symbol_equity = replay_symbol(
            symbol, group, pipeline
        )
        summaries.append(summary)
        trades.extend(symbol_trades)
        equity.extend(symbol_equity)
        print(
            f"  trades={summary['trades']} | "
            f"win_rate={summary['win_rate']}% | "
            f"net_profit={summary['net_profit']} | "
            f"PF={summary['profit_factor']} | "
            f"max_DD={summary['max_drawdown']}"
        )

    summary_df = pd.DataFrame(summaries)
    trades_df = pd.DataFrame(trades)
    equity_df = pd.DataFrame(equity)
    comparison_df = comparison_table(summary_df)

    summary_df.to_csv(REPORT_DIR / "backtest_summary.csv", index=False)
    trades_df.to_csv(REPORT_DIR / "trade_journal.csv", index=False)
    equity_df.to_csv(REPORT_DIR / "equity_curve.csv", index=False)
    comparison_df.to_csv(
        REPORT_DIR / "benchmark_comparison.csv", index=False
    )

    metadata = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_version": "v0.1.0",
        "dataset": str(DATASET_PATH),
        "timeframe": TIMEFRAME,
        "lookback_days": LOOKBACK_DAYS,
        "symbols": list(SYMBOL_RULES),
        "initial_balance_per_symbol": INITIAL_BALANCE,
        "risk_per_trade": RISK_PER_TRADE,
        "taker_fee_rate_per_side": TAKER_FEE_RATE,
        "slippage_rate_per_fill": SLIPPAGE_RATE,
        "entry_signal": "original weighted SignalEngine + optimized symbol filters",
        "execution_and_risk": "src/main_pipeline.py v0.1.0",
        "exit": "v0.1.0 ATR SL/TP plus profitable EMA20 exit",
        "future_columns_used_as_inputs": False,
        "excluded_future_columns": sorted(FUTURE_COLUMNS),
        "intrabar_priority": INTRABAR_PRIORITY,
        "entry_execution": "current completed candle close plus slippage",
    }
    (REPORT_DIR / "backtest_run.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print("")
    print("=" * 72)
    print("BACKTEST COMPLETED")
    print(f"Reports: {REPORT_DIR}")
    print("=" * 72)
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
