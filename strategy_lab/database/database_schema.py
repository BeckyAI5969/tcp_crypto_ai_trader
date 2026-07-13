
"""Schema helpers for the Strategy Lab master trade database."""

from __future__ import annotations

REQUIRED_COLUMNS = {
    "symbol",
    "entry_time",
    "exit_time",
    "entry_price",
    "exit_price",
    "net_profit",
}

PREFERRED_COLUMN_ORDER = [
    "trade_id",
    "strategy_version",
    "source_file",
    "symbol",
    "side",
    "entry_time",
    "exit_time",
    "entry_price",
    "exit_price",
    "quantity",
    "notional",
    "leverage",
    "stop_loss",
    "take_profit",
    "exit_reason",
    "gross_profit",
    "fees",
    "entry_fee",
    "exit_fee",
    "net_profit",
    "result",
    "ai_score",
    "entry_rsi",
    "entry_atr_pct",
    "entry_volume_ratio",
    "entry_ema_gap_pct",
    "balance_after",
]

COLUMN_ALIASES = {
    "gross_pnl": "gross_profit",
    "net_pnl": "net_profit",
    "stop": "stop_loss",
    "tp": "take_profit",
}
