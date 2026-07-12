"""Central configuration for TCP Crypto AI Trader.

Safe defaults:
- Paper trading mode
- Binance testnet enabled
- Live trading disabled
- No API keys stored in source code
"""

from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from typing import Final


TRUE_VALUES: Final[set[str]] = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool) -> bool:
    raw = getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in TRUE_VALUES


def _env_int(name: str, default: int) -> int:
    raw = getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer.") from exc


def _env_float(name: str, default: float) -> float:
    raw = getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be numeric.") from exc


@dataclass(frozen=True)
class Settings:
    # Runtime safety
    execution_mode: str = "PAPER"
    binance_testnet: bool = True
    allow_live_trading: bool = False

    # Market
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    scheduler_seconds: int = 900

    # Strategy gates
    minimum_ai_score: float = 85.0
    minimum_confidence: float = 80.0
    minimum_risk_reward: float = 2.0

    # Risk controls
    max_risk_pct: float = 0.02
    max_leverage: int = 5
    max_margin_usage_pct: float = 0.60
    max_daily_loss_pct: float = 0.05
    max_open_positions: int = 1

    # API credentials are loaded only from environment variables
    binance_api_key: str = ""
    binance_api_secret: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            execution_mode=getenv("TCP_EXECUTION_MODE", "PAPER").upper(),
            binance_testnet=_env_bool("TCP_BINANCE_TESTNET", True),
            allow_live_trading=_env_bool("TCP_ALLOW_LIVE_TRADING", False),
            symbol=getenv("TCP_SYMBOL", "BTCUSDT").upper(),
            timeframe=getenv("TCP_TIMEFRAME", "15m"),
            scheduler_seconds=_env_int("TCP_SCHEDULER_SECONDS", 900),
            minimum_ai_score=_env_float("TCP_MINIMUM_AI_SCORE", 85.0),
            minimum_confidence=_env_float("TCP_MINIMUM_CONFIDENCE", 80.0),
            minimum_risk_reward=_env_float(
                "TCP_MINIMUM_RISK_REWARD",
                2.0,
            ),
            max_risk_pct=_env_float("TCP_MAX_RISK_PCT", 0.02),
            max_leverage=_env_int("TCP_MAX_LEVERAGE", 5),
            max_margin_usage_pct=_env_float(
                "TCP_MAX_MARGIN_USAGE_PCT",
                0.60,
            ),
            max_daily_loss_pct=_env_float(
                "TCP_MAX_DAILY_LOSS_PCT",
                0.05,
            ),
            max_open_positions=_env_int(
                "TCP_MAX_OPEN_POSITIONS",
                1,
            ),
            binance_api_key=getenv("BINANCE_API_KEY", ""),
            binance_api_secret=getenv("BINANCE_API_SECRET", ""),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.execution_mode not in {"PAPER", "TESTNET", "LIVE"}:
            raise ValueError(
                "execution_mode must be PAPER, TESTNET, or LIVE."
            )

        if self.execution_mode == "LIVE" and not self.allow_live_trading:
            raise ValueError(
                "LIVE mode is blocked because allow_live_trading is False."
            )

        if self.execution_mode == "LIVE" and self.binance_testnet:
            raise ValueError(
                "LIVE mode cannot use Binance testnet."
            )

        if not self.symbol:
            raise ValueError("symbol must not be empty.")

        if self.scheduler_seconds < 60:
            raise ValueError(
                "scheduler_seconds must be at least 60."
            )

        if not 0.0 < self.max_risk_pct <= 0.05:
            raise ValueError(
                "max_risk_pct must be greater than 0 and no more than 0.05."
            )

        if not 0.0 < self.max_margin_usage_pct <= 1.0:
            raise ValueError(
                "max_margin_usage_pct must be between 0 and 1."
            )

        if not 0.0 < self.max_daily_loss_pct <= 0.20:
            raise ValueError(
                "max_daily_loss_pct must be greater than 0 and no more than 0.20."
            )

        if self.max_leverage < 1:
            raise ValueError("max_leverage must be at least 1.")

        if self.max_open_positions < 1:
            raise ValueError(
                "max_open_positions must be at least 1."
            )

        if self.execution_mode in {"TESTNET", "LIVE"}:
            if not self.binance_api_key or not self.binance_api_secret:
                raise ValueError(
                    "BINANCE_API_KEY and BINANCE_API_SECRET are required "
                    "for TESTNET or LIVE mode."
                )

    def safe_summary(self) -> dict[str, object]:
        return {
            "execution_mode": self.execution_mode,
            "binance_testnet": self.binance_testnet,
            "allow_live_trading": self.allow_live_trading,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "scheduler_seconds": self.scheduler_seconds,
            "minimum_ai_score": self.minimum_ai_score,
            "minimum_confidence": self.minimum_confidence,
            "minimum_risk_reward": self.minimum_risk_reward,
            "max_risk_pct": self.max_risk_pct,
            "max_leverage": self.max_leverage,
            "max_margin_usage_pct": self.max_margin_usage_pct,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "max_open_positions": self.max_open_positions,
            "api_key_loaded": bool(self.binance_api_key),
            "api_secret_loaded": bool(self.binance_api_secret),
        }


SETTINGS = Settings.from_env()


if __name__ == "__main__":
    print(SETTINGS.safe_summary())