"""AI Score Engine for TCP Crypto AI Trader.

This module converts normalized market features into an explainable score and
trade decision. It is intentionally dependency-free so it can run inside the
current production environment without changing requirements.txt.
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
class ScoreThresholds:
    buy: float = 80.0
    sell: float = 20.0
    minimum_confidence: float = 60.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.sell < self.buy <= 100.0:
            raise ValueError("Thresholds must satisfy 0 <= sell < buy <= 100.")
        if not 0.0 <= self.minimum_confidence <= 100.0:
            raise ValueError("minimum_confidence must be between 0 and 100.")


@dataclass(frozen=True)
class ScoreResult:
    symbol: str
    score: float
    confidence: float
    decision: Decision
    reasons: tuple[str, ...]
    feature_scores: Mapping[str, float]
    weighted_contributions: Mapping[str, float]
    missing_features: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "score": self.score,
            "confidence": self.confidence,
            "decision": self.decision.value,
            "reasons": list(self.reasons),
            "feature_scores": dict(self.feature_scores),
            "weighted_contributions": dict(self.weighted_contributions),
            "missing_features": list(self.missing_features),
        }


class AIScoreEngine:
    """Calculate an explainable 0-100 score from normalized features.

    Expected feature values are in the range 0-100:
      - 0 means strongly bearish / poor quality
      - 50 means neutral
      - 100 means strongly bullish / high quality

    Missing features are permitted. Available weights are re-normalized, while
    confidence is reduced according to feature coverage.
    """

    DEFAULT_WEIGHTS: Mapping[str, float] = {
        "trend": 0.22,
        "momentum": 0.18,
        "ema_alignment": 0.14,
        "macd": 0.10,
        "rsi": 0.08,
        "volume": 0.10,
        "volatility": 0.07,
        "liquidity": 0.06,
        "funding": 0.03,
        "open_interest": 0.02,
    }

    POSITIVE_LABELS: Mapping[str, str] = {
        "trend": "strong trend",
        "momentum": "positive momentum",
        "ema_alignment": "EMA alignment",
        "macd": "supportive MACD",
        "rsi": "healthy RSI",
        "volume": "rising volume",
        "volatility": "healthy volatility",
        "liquidity": "good liquidity",
        "funding": "supportive funding",
        "open_interest": "supportive open interest",
    }

    NEGATIVE_LABELS: Mapping[str, str] = {
        "trend": "weak trend",
        "momentum": "negative momentum",
        "ema_alignment": "bearish EMA alignment",
        "macd": "weak MACD",
        "rsi": "unfavorable RSI",
        "volume": "weak volume",
        "volatility": "unfavorable volatility",
        "liquidity": "poor liquidity",
        "funding": "unfavorable funding",
        "open_interest": "weak open interest",
    }

    def __init__(
        self,
        weights: Mapping[str, float] | None = None,
        thresholds: ScoreThresholds | None = None,
    ) -> None:
        self.weights = self._validate_weights(weights or self.DEFAULT_WEIGHTS)
        self.thresholds = thresholds or ScoreThresholds()

    @staticmethod
    def _validate_weights(weights: Mapping[str, float]) -> dict[str, float]:
        if not weights:
            raise ValueError("At least one feature weight is required.")

        validated: dict[str, float] = {}
        for name, weight in weights.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Feature names must be non-empty strings.")
            if not isinstance(weight, (int, float)) or not isfinite(float(weight)):
                raise ValueError(f"Invalid weight for feature '{name}'.")
            if float(weight) < 0.0:
                raise ValueError(f"Weight for feature '{name}' cannot be negative.")
            validated[name] = float(weight)

        if sum(validated.values()) <= 0.0:
            raise ValueError("The total feature weight must be greater than zero.")

        return validated

    @staticmethod
    def _validate_feature_value(name: str, value: object) -> float:
        if not isinstance(value, (int, float)):
            raise TypeError(f"Feature '{name}' must be numeric.")
        value = float(value)
        if not isfinite(value):
            raise ValueError(f"Feature '{name}' must be finite.")
        if not 0.0 <= value <= 100.0:
            raise ValueError(f"Feature '{name}' must be between 0 and 100.")
        return value

    def evaluate(self, symbol: str, features: Mapping[str, float]) -> ScoreResult:
        if not symbol or not symbol.strip():
            raise ValueError("symbol must be a non-empty string.")

        available: dict[str, float] = {}
        missing: list[str] = []

        for feature_name in self.weights:
            if feature_name not in features or features[feature_name] is None:
                missing.append(feature_name)
                continue
            available[feature_name] = self._validate_feature_value(
                feature_name,
                features[feature_name],
            )

        if not available:
            return ScoreResult(
                symbol=symbol.upper(),
                score=50.0,
                confidence=0.0,
                decision=Decision.WAIT,
                reasons=("No valid scoring features available.",),
                feature_scores={},
                weighted_contributions={},
                missing_features=tuple(missing),
            )

        available_weight = sum(self.weights[name] for name in available)
        total_weight = sum(self.weights.values())
        coverage = available_weight / total_weight

        contributions: dict[str, float] = {}
        score = 0.0
        for name, value in available.items():
            normalized_weight = self.weights[name] / available_weight
            contribution = value * normalized_weight
            contributions[name] = round(contribution, 4)
            score += contribution

        score = round(max(0.0, min(100.0, score)), 2)

        dispersion = (
            sum(abs(value - score) for value in available.values()) / len(available)
        )
        agreement_factor = max(0.0, 1.0 - (dispersion / 50.0))
        confidence = round(
            max(0.0, min(100.0, coverage * agreement_factor * 100.0)),
            2,
        )

        decision = self._make_decision(score, confidence)
        reasons = self._build_reasons(
            decision=decision,
            score=score,
            confidence=confidence,
            available=available,
            missing=missing,
        )

        return ScoreResult(
            symbol=symbol.upper(),
            score=score,
            confidence=confidence,
            decision=decision,
            reasons=tuple(reasons),
            feature_scores=dict(available),
            weighted_contributions=contributions,
            missing_features=tuple(missing),
        )

    def _make_decision(self, score: float, confidence: float) -> Decision:
        if confidence < self.thresholds.minimum_confidence:
            return Decision.WAIT
        if score >= self.thresholds.buy:
            return Decision.BUY
        if score <= self.thresholds.sell:
            return Decision.SELL
        return Decision.WAIT

    def _build_reasons(
        self,
        *,
        decision: Decision,
        score: float,
        confidence: float,
        available: Mapping[str, float],
        missing: list[str],
    ) -> list[str]:
        ranked = sorted(
            available.items(),
            key=lambda item: abs(item[1] - 50.0) * self.weights[item[0]],
            reverse=True,
        )

        reasons: list[str] = []
        for name, value in ranked[:4]:
            if value >= 65.0:
                label = self.POSITIVE_LABELS.get(name, name.replace("_", " "))
                reasons.append(f"{label}: {value:.1f}")
            elif value <= 35.0:
                label = self.NEGATIVE_LABELS.get(name, name.replace("_", " "))
                reasons.append(f"{label}: {value:.1f}")

        if confidence < self.thresholds.minimum_confidence:
            reasons.insert(
                0,
                f"Confidence {confidence:.1f}% is below "
                f"{self.thresholds.minimum_confidence:.1f}%.",
            )
        elif decision is Decision.WAIT:
            reasons.insert(0, f"Score {score:.1f} is inside the WAIT zone.")
        else:
            reasons.insert(
                0,
                f"{decision.value} threshold passed with score {score:.1f}.",
            )

        if missing:
            reasons.append(f"Missing features: {', '.join(missing)}.")

        return reasons


if __name__ == "__main__":
    engine = AIScoreEngine()
    sample = {
        "trend": 90,
        "momentum": 86,
        "ema_alignment": 92,
        "macd": 84,
        "rsi": 72,
        "volume": 81,
        "volatility": 75,
        "liquidity": 88,
        "funding": 60,
        "open_interest": 70,
    }
    print(engine.evaluate("BTCUSDT", sample).as_dict())