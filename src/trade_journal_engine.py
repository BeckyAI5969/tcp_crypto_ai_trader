import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd


class TradeJournalEngine:
    """
    Records every important trading decision, including:
    - 15m strategy signals
    - 5m confirmations
    - 1m entry decisions
    - risk approvals and rejections
    - position open, update, and close events
    - connection and recovery events
    """

    JOURNAL_COLUMNS = [
        "timestamp",
        "event_type",
        "stage",
        "symbol",
        "side",
        "decision",
        "reason",
        "price",
        "strategy_score",
        "confirmation_score",
        "entry_score",
        "atr",
        "rsi14",
        "macd",
        "macd_signal",
        "ema20",
        "ema50",
        "ema200",
        "volume",
        "volume_ma20",
        "leverage",
        "quantity",
        "notional_value",
        "required_margin",
        "risk_amount",
        "stop_loss",
        "take_profit",
        "realized_pnl",
        "unrealized_pnl",
        "exit_reason",
        "holding_seconds",
        "margin_used",
        "free_margin",
        "margin_usage_pct",
        "open_risk",
        "open_risk_pct",
        "open_positions",
        "equity",
        "metadata",
    ]

    def __init__(
        self,
        log_dir: str = "logs",
    ):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.csv_file = (
            self.log_dir / "trade_journal.csv"
        )

        self.jsonl_file = (
            self.log_dir / "trade_journal.jsonl"
        )

    def record(
        self,
        event_type: str,
        stage: str,
        symbol: str = "",
        side: str = "",
        decision: str = "",
        reason: str = "",
        price: float = 0.0,
        strategy_score: float = 0.0,
        confirmation_score: float = 0.0,
        entry_score: float = 0.0,
        indicators: Optional[dict] = None,
        position: Any = None,
        portfolio_summary: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> dict:

        indicators = indicators or {}
        portfolio_summary = portfolio_summary or {}
        metadata = metadata or {}

        position_data = self._position_data(position)

        record = {
            "timestamp": datetime.now().isoformat(),
            "event_type": str(event_type).upper(),
            "stage": str(stage).upper(),
            "symbol": str(symbol).upper(),
            "side": str(
                position_data.get(
                    "side",
                    side,
                )
            ).upper(),
            "decision": str(decision).upper(),
            "reason": str(reason),
            "price": self._number(price),
            "strategy_score":
                self._number(strategy_score),
            "confirmation_score":
                self._number(confirmation_score),
            "entry_score":
                self._number(entry_score),
            "atr": self._number(
                indicators.get(
                    "ATR14",
                    indicators.get("atr", 0.0),
                )
            ),
            "rsi14": self._number(
                indicators.get("RSI14", 0.0)
            ),
            "macd": self._number(
                indicators.get("MACD", 0.0)
            ),
            "macd_signal": self._number(
                indicators.get("MACD_SIGNAL", 0.0)
            ),
            "ema20": self._number(
                indicators.get("EMA20", 0.0)
            ),
            "ema50": self._number(
                indicators.get("EMA50", 0.0)
            ),
            "ema200": self._number(
                indicators.get("EMA200", 0.0)
            ),
            "volume": self._number(
                indicators.get("volume", 0.0)
            ),
            "volume_ma20": self._number(
                indicators.get("VOLUME_MA20", 0.0)
            ),
            "leverage": int(
                position_data.get("leverage", 0)
                or 0
            ),
            "quantity": self._number(
                position_data.get("quantity", 0.0)
            ),
            "notional_value": self._number(
                position_data.get(
                    "notional_value",
                    0.0,
                )
            ),
            "required_margin": self._number(
                position_data.get(
                    "required_margin",
                    0.0,
                )
            ),
            "risk_amount": self._number(
                position_data.get("risk_amount", 0.0)
            ),
            "stop_loss": self._number(
                position_data.get("stop_loss", 0.0)
            ),
            "take_profit": self._number(
                position_data.get("take_profit", 0.0)
            ),
            "realized_pnl": self._number(
                position_data.get("realized_pnl", 0.0)
            ),
            "unrealized_pnl": self._number(
                position_data.get(
                    "unrealized_pnl",
                    0.0,
                )
            ),
            "exit_reason": str(
                position_data.get("exit_reason", "")
            ),
            "holding_seconds": self._number(
                position_data.get(
                    "holding_seconds",
                    0.0,
                )
            ),
            "margin_used": self._number(
                portfolio_summary.get(
                    "margin_used",
                    0.0,
                )
            ),
            "free_margin": self._number(
                portfolio_summary.get(
                    "free_margin",
                    0.0,
                )
            ),
            "margin_usage_pct": self._number(
                portfolio_summary.get(
                    "margin_usage_pct",
                    0.0,
                )
            ),
            "open_risk": self._number(
                portfolio_summary.get(
                    "open_risk",
                    0.0,
                )
            ),
            "open_risk_pct": self._number(
                portfolio_summary.get(
                    "open_risk_pct",
                    0.0,
                )
            ),
            "open_positions": int(
                portfolio_summary.get(
                    "open_positions",
                    0,
                )
                or 0
            ),
            "equity": self._number(
                portfolio_summary.get(
                    "equity",
                    0.0,
                )
            ),
            "metadata": json.dumps(
                metadata,
                ensure_ascii=False,
                default=str,
            ),
        }

        self._append_csv(record)
        self._append_jsonl(record)

        return record

    def record_execution_event(
        self,
        event,
        portfolio_summary: Optional[dict] = None,
    ) -> dict:

        details = getattr(event, "details", {}) or {}
        signal = details.get("signal", {}) or {}
        position = details.get("position")

        return self.record(
            event_type=getattr(
                event,
                "action",
                "EVENT",
            ),
            stage=getattr(
                event,
                "stage",
                "EXECUTION",
            ),
            symbol=getattr(event, "symbol", ""),
            side=signal.get("side", ""),
            decision=getattr(event, "action", ""),
            reason=getattr(event, "message", ""),
            price=details.get(
                "price",
                details.get("entry_price", 0.0),
            ),
            strategy_score=signal.get("score", 0.0),
            confirmation_score=details.get(
                "confirmation_score",
                0.0,
            ),
            entry_score=details.get(
                "entry_score",
                0.0,
            ),
            position=position,
            portfolio_summary=portfolio_summary,
            metadata=details,
        )

    def load(self) -> pd.DataFrame:
        if not self.csv_file.exists():
            return pd.DataFrame(
                columns=self.JOURNAL_COLUMNS
            )

        try:
            return pd.read_csv(self.csv_file)
        except (
            pd.errors.ParserError,
            UnicodeDecodeError,
            OSError,
        ):
            return pd.DataFrame(
                columns=self.JOURNAL_COLUMNS
            )

    def daily_records(
        self,
        date_text: Optional[str] = None,
    ) -> pd.DataFrame:

        date_text = (
            date_text
            or datetime.now().date().isoformat()
        )

        frame = self.load()

        if frame.empty:
            return frame

        timestamps = pd.to_datetime(
            frame["timestamp"],
            errors="coerce",
        )

        return frame[
            timestamps.dt.date.astype(str)
            == date_text
        ].copy()

    def summary(
        self,
        date_text: Optional[str] = None,
    ) -> dict:

        frame = self.daily_records(date_text)

        if frame.empty:
            return {
                "records": 0,
                "signals": 0,
                "confirmations": 0,
                "entries": 0,
                "opens": 0,
                "closes": 0,
                "rejections": 0,
            }

        event_types = (
            frame["event_type"]
            .astype(str)
            .str.upper()
        )

        stages = (
            frame["stage"]
            .astype(str)
            .str.upper()
        )

        return {
            "records": int(len(frame)),
            "signals": int(
                stages.str.contains(
                    "15M_SIGNAL",
                    na=False,
                ).sum()
            ),
            "confirmations": int(
                (
                    stages.str.contains(
                        "5M_CONFIRMATION",
                        na=False,
                    )
                    & event_types.eq("CONFIRM")
                ).sum()
            ),
            "entries": int(
                stages.str.contains(
                    "1M_ENTRY",
                    na=False,
                ).sum()
            ),
            "opens": int(
                event_types.eq("EXECUTE").sum()
                + event_types.eq(
                    "POSITION_OPENED"
                ).sum()
            ),
            "closes": int(
                event_types.eq("CLOSE").sum()
                + event_types.eq(
                    "POSITION_CLOSED"
                ).sum()
            ),
            "rejections": int(
                event_types.eq("REJECT").sum()
                + event_types.eq(
                    "RISK_REJECTED"
                ).sum()
            ),
        }

    def _append_csv(self, record: dict):
        frame = pd.DataFrame(
            [record],
            columns=self.JOURNAL_COLUMNS,
        )

        if self.csv_file.exists():
            frame.to_csv(
                self.csv_file,
                mode="a",
                header=False,
                index=False,
            )
        else:
            frame.to_csv(
                self.csv_file,
                index=False,
            )

    def _append_jsonl(self, record: dict):
        with open(
            self.jsonl_file,
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    default=str,
                )
                + "\n"
            )

    @staticmethod
    def _position_data(position: Any) -> dict:
        if position is None:
            return {}

        if isinstance(position, dict):
            return position

        if hasattr(position, "to_dict"):
            return position.to_dict()

        return {}

    @staticmethod
    def _number(value: Any) -> float:
        try:
            if value is None:
                return 0.0

            return round(float(value), 8)

        except (
            TypeError,
            ValueError,
        ):
            return 0.0