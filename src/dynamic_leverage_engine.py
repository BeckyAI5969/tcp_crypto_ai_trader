"""Dynamic leverage engine for TCP Crypto AI Trader.

Selects leverage from market volatility, AI confidence, symbol-specific caps,
and current portfolio margin usage. This module does not place orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from typing import Mapping


class VolatilityRegime(str, Enum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


@dataclass(frozen=True)
class LeverageDecision:
    approved: bool
    reason: str

    symbol: str
    leverage: int
    maximum_allowed_leverage: int

    volatility_pct: float
    volatility_regime: VolatilityRegime

    confidence: float
    margin_usage_pct: float

    def as_dict(self) -> dict[str, object]:
        return {
            "approved": self.approved,
            "reason": self.reason,
            "symbol": self.symbol,
            "leverage": self.leverage,
            "maximum_allowed_leverage":
                self.maximum_allowed_leverage,
            "volatility_pct": self.volatility_pct,
            "volatility_regime":
                self.volatility_regime.value,
            "confidence": self.confidence,
            "margin_usage_pct": self.margin_usage_pct,
        }


class DynamicLeverageEngine:
    """Choose conservative leverage within symbol-specific hard limits.

    Default hard limits:
      - BTCUSDT: 10x
      - Other configured symbols: 5x
      - Unknown symbols: 3x

    The selected leverage is normally below the hard limit. Confidence may
    increase it slightly, while high volatility or portfolio margin usage
    reduces it. Extreme conditions reject the trade.
    """

    DEFAULT_SYMBOL_CAPS: Mapping[str, int] = {
        "BTCUSDT": 10,
        "ETHUSDT": 5,
        "SOLUSDT": 5,
        "XRPUSDT": 5,
        "BNBUSDT": 5,
    }

    def __init__(
        self,
        *,
        symbol_caps: Mapping[str, int] | None = None,
        unknown_symbol_cap: int = 3,
        minimum_confidence: float = 80.0,
        maximum_margin_usage_pct: float = 0.60,
        high_margin_usage_pct: float = 0.45,
        extreme_volatility_pct: float = 0.05,
    ):
        self.symbol_caps = self._validate_symbol_caps(
            symbol_caps or self.DEFAULT_SYMBOL_CAPS
        )

        if not isinstance(unknown_symbol_cap, int) \
                or unknown_symbol_cap < 1:
            raise ValueError(
                "unknown_symbol_cap must be an integer "
                "greater than zero."
            )

        self.unknown_symbol_cap = unknown_symbol_cap
        self.minimum_confidence = self._validate_percentage(
            "minimum_confidence",
            minimum_confidence,
        )
        self.maximum_margin_usage_pct = self._validate_ratio(
            "maximum_margin_usage_pct",
            maximum_margin_usage_pct,
        )
        self.high_margin_usage_pct = self._validate_ratio(
            "high_margin_usage_pct",
            high_margin_usage_pct,
        )
        self.extreme_volatility_pct = self._validate_ratio(
            "extreme_volatility_pct",
            extreme_volatility_pct,
        )

        if self.high_margin_usage_pct >= \
                self.maximum_margin_usage_pct:
            raise ValueError(
                "high_margin_usage_pct must be lower than "
                "maximum_margin_usage_pct."
            )

    def evaluate(
        self,
        *,
        symbol: str,
        confidence: float,
        volatility_pct: float,
        margin_usage_pct: float = 0.0,
    ) -> LeverageDecision:

        if not symbol or not symbol.strip():
            raise ValueError(
                "symbol must be a non-empty string."
            )

        symbol = symbol.upper()
        confidence = self._validate_percentage(
            "confidence",
            confidence,
        )
        volatility_pct = self._validate_ratio(
            "volatility_pct",
            volatility_pct,
        )
        margin_usage_pct = self._validate_ratio(
            "margin_usage_pct",
            margin_usage_pct,
        )

        maximum_allowed = self.symbol_caps.get(
            symbol,
            self.unknown_symbol_cap,
        )

        regime = self._classify_volatility(
            volatility_pct
        )

        if confidence < self.minimum_confidence:
            return self._rejected(
                symbol=symbol,
                reason=(
                    f"Confidence {confidence:.1f}% is below "
                    f"{self.minimum_confidence:.1f}%."
                ),
                maximum_allowed=maximum_allowed,
                volatility_pct=volatility_pct,
                regime=regime,
                confidence=confidence,
                margin_usage_pct=margin_usage_pct,
            )

        if margin_usage_pct >= \
                self.maximum_margin_usage_pct:
            return self._rejected(
                symbol=symbol,
                reason=(
                    "Portfolio margin usage limit reached."
                ),
                maximum_allowed=maximum_allowed,
                volatility_pct=volatility_pct,
                regime=regime,
                confidence=confidence,
                margin_usage_pct=margin_usage_pct,
            )

        if regime is VolatilityRegime.EXTREME:
            return self._rejected(
                symbol=symbol,
                reason=(
                    "Extreme volatility: trade rejected."
                ),
                maximum_allowed=maximum_allowed,
                volatility_pct=volatility_pct,
                regime=regime,
                confidence=confidence,
                margin_usage_pct=margin_usage_pct,
            )

        leverage = self._base_leverage(regime)

        if confidence >= 95.0:
            leverage += 2
        elif confidence >= 90.0:
            leverage += 1

        if margin_usage_pct >= \
                self.high_margin_usage_pct:
            leverage -= 1

        leverage = max(
            1,
            min(
                leverage,
                maximum_allowed,
            ),
        )

        reason = (
            f"{regime.value} volatility, "
            f"confidence {confidence:.1f}%, "
            f"margin usage "
            f"{margin_usage_pct * 100:.1f}%."
        )

        return LeverageDecision(
            approved=True,
            reason=reason,
            symbol=symbol,
            leverage=leverage,
            maximum_allowed_leverage=maximum_allowed,
            volatility_pct=round(
                volatility_pct,
                8,
            ),
            volatility_regime=regime,
            confidence=round(
                confidence,
                2,
            ),
            margin_usage_pct=round(
                margin_usage_pct,
                8,
            ),
        )

    def _classify_volatility(
        self,
        volatility_pct: float,
    ) -> VolatilityRegime:

        if volatility_pct >= \
                self.extreme_volatility_pct:
            return VolatilityRegime.EXTREME

        if volatility_pct >= 0.03:
            return VolatilityRegime.HIGH

        if volatility_pct >= 0.015:
            return VolatilityRegime.NORMAL

        if volatility_pct >= 0.0075:
            return VolatilityRegime.LOW

        return VolatilityRegime.VERY_LOW

    @staticmethod
    def _base_leverage(
        regime: VolatilityRegime,
    ) -> int:

        mapping = {
            VolatilityRegime.VERY_LOW: 5,
            VolatilityRegime.LOW: 4,
            VolatilityRegime.NORMAL: 3,
            VolatilityRegime.HIGH: 2,
            VolatilityRegime.EXTREME: 1,
        }

        return mapping[regime]

    def _rejected(
        self,
        *,
        symbol: str,
        reason: str,
        maximum_allowed: int,
        volatility_pct: float,
        regime: VolatilityRegime,
        confidence: float,
        margin_usage_pct: float,
    ) -> LeverageDecision:

        return LeverageDecision(
            approved=False,
            reason=reason,
            symbol=symbol,
            leverage=0,
            maximum_allowed_leverage=maximum_allowed,
            volatility_pct=round(
                volatility_pct,
                8,
            ),
            volatility_regime=regime,
            confidence=round(
                confidence,
                2,
            ),
            margin_usage_pct=round(
                margin_usage_pct,
                8,
            ),
        )

    @staticmethod
    def _validate_symbol_caps(
        caps: Mapping[str, int],
    ) -> dict[str, int]:

        if not caps:
            raise ValueError(
                "At least one symbol leverage cap "
                "is required."
            )

        validated: dict[str, int] = {}

        for symbol, cap in caps.items():
            if not symbol or not symbol.strip():
                raise ValueError(
                    "Symbol names must be non-empty."
                )

            if not isinstance(cap, int) or cap < 1:
                raise ValueError(
                    f"Invalid leverage cap for {symbol}."
                )

            validated[symbol.upper()] = cap

        return validated

    @staticmethod
    def _validate_percentage(
        name: str,
        value: float,
    ) -> float:

        if not isinstance(value, (int, float)):
            raise TypeError(
                f"{name} must be numeric."
            )

        value = float(value)

        if not isfinite(value) \
                or not 0.0 <= value <= 100.0:
            raise ValueError(
                f"{name} must be between 0 and 100."
            )

        return value

    @staticmethod
    def _validate_ratio(
        name: str,
        value: float,
    ) -> float:

        if not isinstance(value, (int, float)):
            raise TypeError(
                f"{name} must be numeric."
            )

        value = float(value)

        if not isfinite(value) \
                or not 0.0 <= value <= 1.0:
            raise ValueError(
                f"{name} must be between 0 and 1."
            )

        return value


if __name__ == "__main__":
    engine = DynamicLeverageEngine()

    btc_result = engine.evaluate(
        symbol="BTCUSDT",
        confidence=95.0,
        volatility_pct=0.012,
        margin_usage_pct=0.20,
    )

    altcoin_result = engine.evaluate(
        symbol="SOLUSDT",
        confidence=90.0,
        volatility_pct=0.025,
        margin_usage_pct=0.20,
    )

    print("BTC:", btc_result.as_dict())
    print("SOL:", altcoin_result.as_dict())