"""Position size calculator for TCP Crypto AI Trader.

Calculates quantity, notional value, required margin, and expected loss from
account balance, risk percentage, entry price, stop-loss price, and leverage.
This module does not place orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class PositionSizeCalculation:
    approved: bool
    reason: str

    quantity: float
    notional_value: float
    required_margin: float

    risk_amount: float
    risk_pct: float

    entry_price: float
    stop_loss: float
    stop_distance: float
    stop_distance_pct: float

    leverage: int
    margin_usage_pct: float

    def as_dict(self) -> dict[str, object]:
        return {
            "approved": self.approved,
            "reason": self.reason,
            "quantity": self.quantity,
            "notional_value": self.notional_value,
            "required_margin": self.required_margin,
            "risk_amount": self.risk_amount,
            "risk_pct": self.risk_pct,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "stop_distance": self.stop_distance,
            "stop_distance_pct": self.stop_distance_pct,
            "leverage": self.leverage,
            "margin_usage_pct": self.margin_usage_pct,
        }


class PositionSizeCalculator:

    def __init__(
        self,
        *,
        max_margin_usage_pct: float = 0.60,
        minimum_stop_distance_pct: float = 0.001,
        maximum_stop_distance_pct: float = 0.10,
        minimum_notional_value: float = 5.0,
    ):
        self.max_margin_usage_pct = self._validate_ratio(
            "max_margin_usage_pct",
            max_margin_usage_pct,
        )
        self.minimum_stop_distance_pct = self._validate_ratio(
            "minimum_stop_distance_pct",
            minimum_stop_distance_pct,
        )
        self.maximum_stop_distance_pct = self._validate_ratio(
            "maximum_stop_distance_pct",
            maximum_stop_distance_pct,
        )

        if (
            self.minimum_stop_distance_pct
            >= self.maximum_stop_distance_pct
        ):
            raise ValueError(
                "minimum_stop_distance_pct must be lower than "
                "maximum_stop_distance_pct."
            )

        self.minimum_notional_value = self._validate_positive(
            "minimum_notional_value",
            minimum_notional_value,
        )

    def calculate(
        self,
        *,
        account_balance: float,
        risk_pct: float,
        entry_price: float,
        stop_loss: float,
        leverage: int,
        free_margin: float | None = None,
    ) -> PositionSizeCalculation:

        account_balance = self._validate_positive(
            "account_balance",
            account_balance,
        )
        risk_pct = self._validate_ratio(
            "risk_pct",
            risk_pct,
        )
        entry_price = self._validate_positive(
            "entry_price",
            entry_price,
        )
        stop_loss = self._validate_positive(
            "stop_loss",
            stop_loss,
        )

        if not isinstance(leverage, int) or leverage < 1:
            raise ValueError("leverage must be an integer greater than zero.")

        if free_margin is None:
            free_margin = account_balance
        else:
            free_margin = self._validate_non_negative(
                "free_margin",
                free_margin,
            )

        stop_distance = abs(entry_price - stop_loss)
        stop_distance_pct = stop_distance / entry_price

        if stop_distance <= 0.0:
            return self._rejected(
                reason="Stop-loss distance must be greater than zero.",
                account_balance=account_balance,
                risk_pct=risk_pct,
                entry_price=entry_price,
                stop_loss=stop_loss,
                leverage=leverage,
                stop_distance=0.0,
                stop_distance_pct=0.0,
            )

        if stop_distance_pct < self.minimum_stop_distance_pct:
            return self._rejected(
                reason="Stop-loss distance is too tight.",
                account_balance=account_balance,
                risk_pct=risk_pct,
                entry_price=entry_price,
                stop_loss=stop_loss,
                leverage=leverage,
                stop_distance=stop_distance,
                stop_distance_pct=stop_distance_pct,
            )

        if stop_distance_pct > self.maximum_stop_distance_pct:
            return self._rejected(
                reason="Stop-loss distance is too wide.",
                account_balance=account_balance,
                risk_pct=risk_pct,
                entry_price=entry_price,
                stop_loss=stop_loss,
                leverage=leverage,
                stop_distance=stop_distance,
                stop_distance_pct=stop_distance_pct,
            )

        risk_amount = account_balance * risk_pct
        quantity = risk_amount / stop_distance
        notional_value = quantity * entry_price
        required_margin = notional_value / leverage

        maximum_allowed_margin = min(
            account_balance * self.max_margin_usage_pct,
            free_margin,
        )

        if required_margin > maximum_allowed_margin:
            required_margin = maximum_allowed_margin
            notional_value = required_margin * leverage
            quantity = notional_value / entry_price
            risk_amount = quantity * stop_distance

        if notional_value < self.minimum_notional_value:
            return self._rejected(
                reason="Calculated notional value is below the minimum.",
                account_balance=account_balance,
                risk_pct=risk_pct,
                entry_price=entry_price,
                stop_loss=stop_loss,
                leverage=leverage,
                stop_distance=stop_distance,
                stop_distance_pct=stop_distance_pct,
            )

        margin_usage_pct = (
            required_margin / account_balance
            if account_balance > 0.0
            else 0.0
        )

        return PositionSizeCalculation(
            approved=True,
            reason="Approved",
            quantity=round(quantity, 8),
            notional_value=round(notional_value, 8),
            required_margin=round(required_margin, 8),
            risk_amount=round(risk_amount, 8),
            risk_pct=round(
                risk_amount / account_balance,
                8,
            ),
            entry_price=round(entry_price, 8),
            stop_loss=round(stop_loss, 8),
            stop_distance=round(stop_distance, 8),
            stop_distance_pct=round(stop_distance_pct, 8),
            leverage=leverage,
            margin_usage_pct=round(margin_usage_pct, 8),
        )

    def _rejected(
        self,
        *,
        reason: str,
        account_balance: float,
        risk_pct: float,
        entry_price: float,
        stop_loss: float,
        leverage: int,
        stop_distance: float,
        stop_distance_pct: float,
    ) -> PositionSizeCalculation:

        return PositionSizeCalculation(
            approved=False,
            reason=reason,
            quantity=0.0,
            notional_value=0.0,
            required_margin=0.0,
            risk_amount=0.0,
            risk_pct=round(risk_pct, 8),
            entry_price=round(entry_price, 8),
            stop_loss=round(stop_loss, 8),
            stop_distance=round(stop_distance, 8),
            stop_distance_pct=round(stop_distance_pct, 8),
            leverage=leverage,
            margin_usage_pct=0.0,
        )

    @staticmethod
    def _validate_positive(name: str, value: float) -> float:
        if not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be numeric.")

        value = float(value)

        if not isfinite(value) or value <= 0.0:
            raise ValueError(
                f"{name} must be a finite number greater than zero."
            )

        return value

    @staticmethod
    def _validate_non_negative(name: str, value: float) -> float:
        if not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be numeric.")

        value = float(value)

        if not isfinite(value) or value < 0.0:
            raise ValueError(
                f"{name} must be a finite non-negative number."
            )

        return value

    @staticmethod
    def _validate_ratio(name: str, value: float) -> float:
        if not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be numeric.")

        value = float(value)

        if not isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(
                f"{name} must be between 0 and 1."
            )

        return value


if __name__ == "__main__":
    calculator = PositionSizeCalculator()

    result = calculator.calculate(
        account_balance=1000.0,
        free_margin=1000.0,
        risk_pct=0.02,
        entry_price=60000.0,
        stop_loss=59400.0,
        leverage=3,
    )

    print(result.as_dict())