"""Multi-timeframe confirmation engine for TCP Crypto AI Trader.

This module combines per-timeframe BUY/SELL/WAIT decisions into one explainable
confirmation result. It is dependency-free and does not place orders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Mapping


class Decision(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"


@dataclass(frozen=True)
class TimeframeSignal:
    timeframe: str
    decision: Decision
    score: float
    confidence: float
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.timeframe or not self.timeframe.strip():
            raise ValueError("timeframe must be a non-empty string.")
        if not isfinite(float(self.score)) or not 0.0 <= float(self.score) <= 100.0:
            raise ValueError("score must be between 0 and 100.")
        if (
            not isfinite(float(self.confidence))
            or not 0.0 <= float(self.confidence) <= 100.0
        ):
            raise ValueError("confidence must be between 0 and 100.")


@dataclass(frozen=True)
class ConfirmationResult:
    symbol: str
    decision: Decision
    confirmation_score: float
    confidence: float
    aligned_timeframes: tuple[str, ...]
    conflicting_timeframes: tuple[str, ...]
    missing_timeframes: tuple[str, ...]
    reasons: tuple[str, ...]
    timeframe_details: Mapping[str, Mapping[str, object]]

    def as_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "decision": self.decision.value,
            "confirmation_score": self.confirmation_score,
            "confidence": self.confidence,
            "aligned_timeframes": list(self.aligned_timeframes),
            "conflicting_timeframes": list(self.conflicting_timeframes),
            "missing_timeframes": list(self.missing_timeframes),
            "reasons": list(self.reasons),
            "timeframe_details": {
                key: dict(value) for key, value in self.timeframe_details.items()
            },
        }


class TimeframeConfirmationEngine:
    """Confirm trade direction across multiple timeframes.

    The default weighting emphasizes the higher timeframe:
      1m = 0.20
      5m = 0.30
      15m = 0.50

    A final BUY or SELL requires:
      - enough weighted directional agreement,
      - minimum combined confidence,
      - no strong higher-timeframe conflict.
    """

    DEFAULT_WEIGHTS: Mapping[str, float] = {
        "1m": 0.20,
        "5m": 0.30,
        "15m": 0.50,
    }

    def __init__(
        self,
        timeframe_weights: Mapping[str, float] | None = None,
        *,
        minimum_alignment: float = 0.70,
        minimum_confidence: float = 60.0,
        higher_timeframe: str = "15m",
        higher_timeframe_min_confidence: float = 55.0,
    ) -> None:
        self.timeframe_weights = self._validate_weights(
            timeframe_weights or self.DEFAULT_WEIGHTS
        )
        self.minimum_alignment = self._validate_ratio(
            "minimum_alignment",
            minimum_alignment,
        )
        self.minimum_confidence = self._validate_percentage(
            "minimum_confidence",
            minimum_confidence,
        )
        self.higher_timeframe = higher_timeframe
        self.higher_timeframe_min_confidence = self._validate_percentage(
            "higher_timeframe_min_confidence",
            higher_timeframe_min_confidence,
        )

    @staticmethod
    def _validate_weights(weights: Mapping[str, float]) -> dict[str, float]:
        if not weights:
            raise ValueError("At least one timeframe weight is required.")

        validated: dict[str, float] = {}
        for timeframe, weight in weights.items():
            if not timeframe or not timeframe.strip():
                raise ValueError("Timeframe names must be non-empty strings.")
            if not isinstance(weight, (int, float)) or not isfinite(float(weight)):
                raise ValueError(f"Invalid weight for timeframe '{timeframe}'.")
            if float(weight) < 0.0:
                raise ValueError(
                    f"Weight for timeframe '{timeframe}' cannot be negative."
                )
            validated[timeframe] = float(weight)

        if sum(validated.values()) <= 0.0:
            raise ValueError("The total timeframe weight must be greater than zero.")

        return validated

    @staticmethod
    def _validate_ratio(name: str, value: float) -> float:
        if not isinstance(value, (int, float)) or not isfinite(float(value)):
            raise ValueError(f"{name} must be a finite number.")
        value = float(value)
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be between 0 and 1.")
        return value

    @staticmethod
    def _validate_percentage(name: str, value: float) -> float:
        if not isinstance(value, (int, float)) or not isfinite(float(value)):
            raise ValueError(f"{name} must be a finite number.")
        value = float(value)
        if not 0.0 <= value <= 100.0:
            raise ValueError(f"{name} must be between 0 and 100.")
        return value

    @staticmethod
    def _coerce_signal(
        timeframe: str,
        raw_signal: TimeframeSignal | Mapping[str, object],
    ) -> TimeframeSignal:
        if isinstance(raw_signal, TimeframeSignal):
            return raw_signal

        if not isinstance(raw_signal, Mapping):
            raise TypeError(
                f"Signal for timeframe '{timeframe}' must be "
                "TimeframeSignal or mapping."
            )

        raw_decision = raw_signal.get("decision", Decision.WAIT)
        try:
            decision = (
                raw_decision
                if isinstance(raw_decision, Decision)
                else Decision(str(raw_decision).upper())
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid decision for timeframe '{timeframe}': {raw_decision}"
            ) from exc

        reasons_value = raw_signal.get("reasons", ())
        if isinstance(reasons_value, str):
            reasons = (reasons_value,)
        else:
            reasons = tuple(str(item) for item in reasons_value or ())

        return TimeframeSignal(
            timeframe=timeframe,
            decision=decision,
            score=float(raw_signal.get("score", 50.0)),
            confidence=float(raw_signal.get("confidence", 0.0)),
            reasons=reasons,
        )

    def evaluate(
        self,
        symbol: str,
        signals: Mapping[str, TimeframeSignal | Mapping[str, object]],
    ) -> ConfirmationResult:
        if not symbol or not symbol.strip():
            raise ValueError("symbol must be a non-empty string.")

        parsed: dict[str, TimeframeSignal] = {}
        missing: list[str] = []

        for timeframe in self.timeframe_weights:
            raw_signal = signals.get(timeframe)
            if raw_signal is None:
                missing.append(timeframe)
                continue
            parsed[timeframe] = self._coerce_signal(timeframe, raw_signal)

        if not parsed:
            return ConfirmationResult(
                symbol=symbol.upper(),
                decision=Decision.WAIT,
                confirmation_score=0.0,
                confidence=0.0,
                aligned_timeframes=(),
                conflicting_timeframes=(),
                missing_timeframes=tuple(missing),
                reasons=("No timeframe signals are available.",),
                timeframe_details={},
            )

        available_weight = sum(
            self.timeframe_weights[timeframe] for timeframe in parsed
        )
        total_weight = sum(self.timeframe_weights.values())
        coverage = available_weight / total_weight

        buy_weight = 0.0
        sell_weight = 0.0
        wait_weight = 0.0
        weighted_confidence = 0.0

        details: dict[str, Mapping[str, object]] = {}

        for timeframe, signal in parsed.items():
            weight = self.timeframe_weights[timeframe]
            normalized_weight = weight / available_weight
            weighted_confidence += signal.confidence * normalized_weight

            if signal.decision is Decision.BUY:
                buy_weight += weight
            elif signal.decision is Decision.SELL:
                sell_weight += weight
            else:
                wait_weight += weight

            details[timeframe] = {
                "decision": signal.decision.value,
                "score": round(signal.score, 2),
                "confidence": round(signal.confidence, 2),
                "weight": round(weight, 4),
                "reasons": list(signal.reasons),
            }

        buy_alignment = buy_weight / available_weight
        sell_alignment = sell_weight / available_weight
        wait_alignment = wait_weight / available_weight

        leading_decision = Decision.WAIT
        leading_alignment = wait_alignment

        if buy_alignment > leading_alignment:
            leading_decision = Decision.BUY
            leading_alignment = buy_alignment
        if sell_alignment > leading_alignment:
            leading_decision = Decision.SELL
            leading_alignment = sell_alignment

        final_confidence = round(
            max(0.0, min(100.0, weighted_confidence * coverage)),
            2,
        )

        higher_timeframe_conflict = self._has_higher_timeframe_conflict(
            leading_decision,
            parsed,
        )

        decision = Decision.WAIT
        reasons: list[str] = []

        if leading_decision is Decision.WAIT:
            reasons.append("WAIT is the dominant multi-timeframe result.")
        elif leading_alignment < self.minimum_alignment:
            reasons.append(
                f"{leading_decision.value} alignment "
                f"{leading_alignment * 100:.1f}% is below "
                f"{self.minimum_alignment * 100:.1f}%."
            )
        elif final_confidence < self.minimum_confidence:
            reasons.append(
                f"Combined confidence {final_confidence:.1f}% is below "
                f"{self.minimum_confidence:.1f}%."
            )
        elif higher_timeframe_conflict:
            reasons.append(
                f"{self.higher_timeframe} conflicts with "
                f"{leading_decision.value} direction."
            )
        else:
            decision = leading_decision
            reasons.append(
                f"{decision.value} confirmed by "
                f"{leading_alignment * 100:.1f}% weighted alignment."
            )

        aligned = tuple(
            timeframe
            for timeframe, signal in parsed.items()
            if signal.decision is decision and decision is not Decision.WAIT
        )

        conflicting = tuple(
            timeframe
            for timeframe, signal in parsed.items()
            if decision is not Decision.WAIT
            and signal.decision not in (decision, Decision.WAIT)
        )

        if decision is Decision.WAIT:
            aligned = tuple(
                timeframe
                for timeframe, signal in parsed.items()
                if signal.decision is leading_decision
            )
            conflicting = tuple(
                timeframe
                for timeframe, signal in parsed.items()
                if signal.decision not in (leading_decision, Decision.WAIT)
            )

        reasons.append(
            f"BUY {buy_alignment * 100:.1f}% | "
            f"SELL {sell_alignment * 100:.1f}% | "
            f"WAIT {wait_alignment * 100:.1f}%."
        )

        if missing:
            reasons.append(f"Missing timeframes: {', '.join(missing)}.")

        return ConfirmationResult(
            symbol=symbol.upper(),
            decision=decision,
            confirmation_score=round(leading_alignment * 100.0, 2),
            confidence=final_confidence,
            aligned_timeframes=aligned,
            conflicting_timeframes=conflicting,
            missing_timeframes=tuple(missing),
            reasons=tuple(reasons),
            timeframe_details=details,
        )

    def _has_higher_timeframe_conflict(
        self,
        leading_decision: Decision,
        signals: Mapping[str, TimeframeSignal],
    ) -> bool:
        if leading_decision is Decision.WAIT:
            return False

        higher_signal = signals.get(self.higher_timeframe)
        if higher_signal is None:
            return False

        if higher_signal.confidence < self.higher_timeframe_min_confidence:
            return False

        return higher_signal.decision not in (leading_decision, Decision.WAIT)


if __name__ == "__main__":
    engine = TimeframeConfirmationEngine()
    sample_signals = {
        "1m": {
            "decision": "BUY",
            "score": 84,
            "confidence": 78,
            "reasons": ["positive momentum"],
        },
        "5m": {
            "decision": "BUY",
            "score": 88,
            "confidence": 82,
            "reasons": ["EMA alignment"],
        },
        "15m": {
            "decision": "BUY",
            "score": 91,
            "confidence": 87,
            "reasons": ["strong trend"],
        },
    }
    print(engine.evaluate("BTCUSDT", sample_signals).as_dict())