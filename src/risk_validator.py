"""Risk validator for TCP Crypto AI Trader."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskValidationResult:
    approved: bool
    reasons: tuple[str, ...]

    def as_dict(self):
        return {
            "approved": self.approved,
            "reasons": list(self.reasons),
        }


class RiskValidator:

    def __init__(
        self,
        *,
        minimum_confidence: float = 80.0,
        minimum_risk_reward: float = 2.0,
        maximum_daily_loss_pct: float = 0.05,
        maximum_open_positions: int = 3,
    ):
        self.minimum_confidence = minimum_confidence
        self.minimum_risk_reward = minimum_risk_reward
        self.maximum_daily_loss_pct = maximum_daily_loss_pct
        self.maximum_open_positions = maximum_open_positions

    def validate(
        self,
        *,
        confidence: float,
        risk_reward: float,
        daily_loss_pct: float,
        open_positions: int,
    ) -> RiskValidationResult:

        reasons = []

        if confidence < self.minimum_confidence:
            reasons.append(
                f"Confidence {confidence:.1f}% below minimum."
            )

        if risk_reward < self.minimum_risk_reward:
            reasons.append(
                f"Risk/Reward {risk_reward:.2f} below minimum."
            )

        if daily_loss_pct >= self.maximum_daily_loss_pct:
            reasons.append(
                "Daily loss limit reached."
            )

        if open_positions >= self.maximum_open_positions:
            reasons.append(
                "Maximum open positions reached."
            )

        return RiskValidationResult(
            approved=len(reasons) == 0,
            reasons=tuple(reasons) if reasons else ("Approved",),
        )


if __name__ == "__main__":
    validator = RiskValidator()

    print(
        validator.validate(
            confidence=91,
            risk_reward=2.6,
            daily_loss_pct=0.01,
            open_positions=1,
        ).as_dict()
    )