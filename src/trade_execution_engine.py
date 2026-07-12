"""Trade execution planning engine for TCP Crypto AI Trader.

This module combines validated outputs from decision, risk, leverage,
position sizing, and exit-planning modules into one immutable execution plan.

It does not place real or paper orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class TradeExecutionInput:
    symbol: str
    side: str
    confidence: float

    entry_price: float
    quantity: float
    notional_value: float
    required_margin: float

    leverage: int
    stop_loss: float
    take_profit: float
    risk_reward: float

    risk_amount: float
    risk_pct: float

    decision_approved: bool
    risk_approved: bool
    leverage_approved: bool
    position_size_approved: bool
    exit_plan_approved: bool


@dataclass(frozen=True)
class TradeExecutionPlan:
    approved: bool
    reason: str

    symbol: str
    side: str
    confidence: float

    entry_price: float
    quantity: float
    notional_value: float
    required_margin: float

    leverage: int
    stop_loss: float
    take_profit: float
    risk_reward: float

    risk_amount: float
    risk_pct: float

    status: str

    def as_dict(self) -> dict[str, object]:
        return {
            "approved": self.approved,
            "reason": self.reason,
            "symbol": self.symbol,
            "side": self.side,
            "confidence": self.confidence,
            "entry_price": self.entry_price,
            "quantity": self.quantity,
            "notional_value": self.notional_value,
            "required_margin": self.required_margin,
            "leverage": self.leverage,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_reward": self.risk_reward,
            "risk_amount": self.risk_amount,
            "risk_pct": self.risk_pct,
            "status": self.status,
        }


class TradeExecutionEngine:
    """Build a final execution plan after all upstream checks pass."""

    def __init__(
        self,
        *,
        minimum_confidence: float = 80.0,
        minimum_risk_reward: float = 2.0,
        maximum_risk_pct: float = 0.02,
    ):
        self.minimum_confidence = self._validate_percentage(
            "minimum_confidence",
            minimum_confidence,
        )
        self.minimum_risk_reward = self._validate_positive(
            "minimum_risk_reward",
            minimum_risk_reward,
        )
        self.maximum_risk_pct = self._validate_ratio(
            "maximum_risk_pct",
            maximum_risk_pct,
        )

    def build_plan(
        self,
        trade_input: TradeExecutionInput,
    ) -> TradeExecutionPlan:

        symbol = self._validate_symbol(trade_input.symbol)
        side = self._validate_side(trade_input.side)

        confidence = self._validate_percentage(
            "confidence",
            trade_input.confidence,
        )
        entry_price = self._validate_positive(
            "entry_price",
            trade_input.entry_price,
        )
        quantity = self._validate_positive(
            "quantity",
            trade_input.quantity,
        )
        notional_value = self._validate_positive(
            "notional_value",
            trade_input.notional_value,
        )
        required_margin = self._validate_positive(
            "required_margin",
            trade_input.required_margin,
        )
        stop_loss = self._validate_positive(
            "stop_loss",
            trade_input.stop_loss,
        )
        take_profit = self._validate_positive(
            "take_profit",
            trade_input.take_profit,
        )
        risk_reward = self._validate_positive(
            "risk_reward",
            trade_input.risk_reward,
        )
        risk_amount = self._validate_non_negative(
            "risk_amount",
            trade_input.risk_amount,
        )
        risk_pct = self._validate_ratio(
            "risk_pct",
            trade_input.risk_pct,
        )

        if not isinstance(trade_input.leverage, int) \
                or trade_input.leverage < 1:
            raise ValueError(
                "leverage must be an integer greater than zero."
            )

        checks = {
            "Decision engine": trade_input.decision_approved,
            "Risk validator": trade_input.risk_approved,
            "Leverage engine": trade_input.leverage_approved,
            "Position sizing": trade_input.position_size_approved,
            "Exit plan": trade_input.exit_plan_approved,
        }

        failed_checks = [
            name for name, approved in checks.items()
            if not approved
        ]

        if failed_checks:
            return self._rejected(
                trade_input=trade_input,
                reason=(
                    "Rejected by: "
                    + ", ".join(failed_checks)
                    + "."
                ),
            )

        if confidence < self.minimum_confidence:
            return self._rejected(
                trade_input=trade_input,
                reason=(
                    f"Confidence {confidence:.2f}% is below "
                    f"{self.minimum_confidence:.2f}%."
                ),
            )

        if risk_reward < self.minimum_risk_reward:
            return self._rejected(
                trade_input=trade_input,
                reason=(
                    f"Risk/reward {risk_reward:.2f} is below "
                    f"{self.minimum_risk_reward:.2f}."
                ),
            )

        if risk_pct > self.maximum_risk_pct:
            return self._rejected(
                trade_input=trade_input,
                reason=(
                    f"Risk {risk_pct * 100:.2f}% exceeds "
                    f"{self.maximum_risk_pct * 100:.2f}%."
                ),
            )

        if not self._prices_match_side(
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        ):
            return self._rejected(
                trade_input=trade_input,
                reason=(
                    "Stop-loss or take-profit is on the wrong "
                    "side of the entry price."
                ),
            )

        return TradeExecutionPlan(
            approved=True,
            reason="All execution checks passed.",
            symbol=symbol,
            side=side,
            confidence=round(confidence, 2),
            entry_price=round(entry_price, 8),
            quantity=round(quantity, 8),
            notional_value=round(notional_value, 8),
            required_margin=round(required_margin, 8),
            leverage=trade_input.leverage,
            stop_loss=round(stop_loss, 8),
            take_profit=round(take_profit, 8),
            risk_reward=round(risk_reward, 2),
            risk_amount=round(risk_amount, 8),
            risk_pct=round(risk_pct, 8),
            status="READY_FOR_PAPER_EXECUTION",
        )

    @staticmethod
    def _prices_match_side(
        *,
        side: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
    ) -> bool:

        if side == "BUY":
            return stop_loss < entry_price < take_profit

        return take_profit < entry_price < stop_loss

    @staticmethod
    def _rejected(
        *,
        trade_input: TradeExecutionInput,
        reason: str,
    ) -> TradeExecutionPlan:

        return TradeExecutionPlan(
            approved=False,
            reason=reason,
            symbol=trade_input.symbol.upper(),
            side=trade_input.side.upper(),
            confidence=round(trade_input.confidence, 2),
            entry_price=round(trade_input.entry_price, 8),
            quantity=round(trade_input.quantity, 8),
            notional_value=round(
                trade_input.notional_value,
                8,
            ),
            required_margin=round(
                trade_input.required_margin,
                8,
            ),
            leverage=trade_input.leverage,
            stop_loss=round(trade_input.stop_loss, 8),
            take_profit=round(trade_input.take_profit, 8),
            risk_reward=round(trade_input.risk_reward, 2),
            risk_amount=round(trade_input.risk_amount, 8),
            risk_pct=round(trade_input.risk_pct, 8),
            status="REJECTED",
        )

    @staticmethod
    def _validate_symbol(symbol: str) -> str:
        if not isinstance(symbol, str) or not symbol.strip():
            raise ValueError(
                "symbol must be a non-empty string."
            )
        return symbol.upper()

    @staticmethod
    def _validate_side(side: str) -> str:
        if not isinstance(side, str):
            raise TypeError("side must be a string.")

        side = side.upper()

        if side not in {"BUY", "SELL"}:
            raise ValueError(
                "side must be BUY or SELL."
            )

        return side

    @staticmethod
    def _validate_percentage(
        name: str,
        value: float,
    ) -> float:

        if not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be numeric.")

        value = float(value)

        if not isfinite(value) or not 0.0 <= value <= 100.0:
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
            raise TypeError(f"{name} must be numeric.")

        value = float(value)

        if not isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(
                f"{name} must be between 0 and 1."
            )

        return value

    @staticmethod
    def _validate_positive(
        name: str,
        value: float,
    ) -> float:

        if not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be numeric.")

        value = float(value)

        if not isfinite(value) or value <= 0.0:
            raise ValueError(
                f"{name} must be greater than zero."
            )

        return value

    @staticmethod
    def _validate_non_negative(
        name: str,
        value: float,
    ) -> float:

        if not isinstance(value, (int, float)):
            raise TypeError(f"{name} must be numeric.")

        value = float(value)

        if not isfinite(value) or value < 0.0:
            raise ValueError(
                f"{name} must be non-negative."
            )

        return value


if __name__ == "__main__":
    engine = TradeExecutionEngine()

    sample_input = TradeExecutionInput(
        symbol="BTCUSDT",
        side="BUY",
        confidence=91.0,
        entry_price=60000.0,
        quantity=0.03,
        notional_value=1800.0,
        required_margin=600.0,
        leverage=3,
        stop_loss=59400.0,
        take_profit=61500.0,
        risk_reward=2.5,
        risk_amount=18.0,
        risk_pct=0.018,
        decision_approved=True,
        risk_approved=True,
        leverage_approved=True,
        position_size_approved=True,
        exit_plan_approved=True,
    )

    print(engine.build_plan(sample_input).as_dict())