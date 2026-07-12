"""Structured JSON logging for TCP Crypto AI Trader.

Creates daily JSON Lines log files under:

    logs/YYYY-MM-DD/

Each log entry is written as one JSON object per line.
Sensitive values such as API keys and secrets are redacted automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Mapping


SENSITIVE_KEYS = {
    "api_key",
    "api_secret",
    "binance_api_key",
    "binance_api_secret",
    "secret",
    "signature",
    "token",
    "password",
}


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): (
                "***REDACTED***"
                if str(key).lower() in SENSITIVE_KEYS
                else _redact(item)
            )
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]

    return value


class JsonLineFormatter(logging.Formatter):
    """Format each log record as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        event_data = getattr(record, "event_data", None)
        if isinstance(event_data, Mapping):
            payload["data"] = _redact(dict(event_data))

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )


@dataclass(frozen=True)
class LoggingConfig:
    base_dir: Path = Path("logs")
    max_bytes: int = 5_000_000
    backup_count: int = 5
    console_enabled: bool = True


class StructuredLogger:
    """Application logger with daily folders and JSONL output."""

    def __init__(
        self,
        name: str,
        *,
        category: str = "pipeline",
        config: LoggingConfig | None = None,
    ) -> None:
        if not name.strip():
            raise ValueError("Logger name must not be empty.")

        if not category.strip():
            raise ValueError("Log category must not be empty.")

        self.config = config or LoggingConfig()
        self.category = category.strip().lower()

        today = datetime.now(UTC).date().isoformat()
        log_dir = self.config.base_dir / today
        log_dir.mkdir(parents=True, exist_ok=True)

        log_path = log_dir / f"{self.category}.log"

        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        if not self._logger.handlers:
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=self.config.max_bytes,
                backupCount=self.config.backup_count,
                encoding="utf-8",
            )
            file_handler.setFormatter(JsonLineFormatter())
            self._logger.addHandler(file_handler)

            if self.config.console_enabled:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(JsonLineFormatter())
                self._logger.addHandler(console_handler)

    def info(
        self,
        message: str,
        **event_data: Any,
    ) -> None:
        self._logger.info(
            message,
            extra={"event_data": event_data},
        )

    def warning(
        self,
        message: str,
        **event_data: Any,
    ) -> None:
        self._logger.warning(
            message,
            extra={"event_data": event_data},
        )

    def error(
        self,
        message: str,
        **event_data: Any,
    ) -> None:
        self._logger.error(
            message,
            extra={"event_data": event_data},
        )

    def exception(
        self,
        message: str,
        **event_data: Any,
    ) -> None:
        self._logger.exception(
            message,
            extra={"event_data": event_data},
        )


def get_pipeline_logger() -> StructuredLogger:
    return StructuredLogger(
        "tcp.pipeline",
        category="pipeline",
    )


def get_trade_logger() -> StructuredLogger:
    return StructuredLogger(
        "tcp.trade",
        category="trade",
    )


def get_risk_logger() -> StructuredLogger:
    return StructuredLogger(
        "tcp.risk",
        category="risk",
    )


def get_error_logger() -> StructuredLogger:
    return StructuredLogger(
        "tcp.error",
        category="error",
    )


if __name__ == "__main__":
    logger = get_pipeline_logger()

    logger.info(
        "Pipeline logging test",
        symbol="BTCUSDT",
        stage="INITIALIZED",
        result="PASS",
        api_secret="must_not_appear",
    )

    print("Structured logging test completed.")