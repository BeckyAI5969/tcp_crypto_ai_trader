"""Stop-loss / Take-profit engine for TCP Crypto AI Trader."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ExitPlan:
    approved: bool
    reason: str
    side: str
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    atr: float

    def as_dict(self):
        return self.__dict__


class StopLossTakeProfitEngine:

    def __init__(
        self,
        atr_multiplier: float = 1.5,
        minimum_rr: float = 2.0,
        target_rr: float = 2.5,
    ):
        self.atr_multiplier = atr_multiplier
        self.minimum_rr = minimum_rr
        self.target_rr = target_rr

    def calculate(
        self,
        *,
        side: str,
        entry_price: float,
        atr: float,
    ) -> ExitPlan:

        side = side.upper()
        if side not in ("BUY", "SELL"):
            return ExitPlan(False, "Invalid side.", side, entry_price, 0, 0, 0, atr)

        for name, value in {"entry_price": entry_price, "atr": atr}.items():
            if not isinstance(value, (int, float)) or not isfinite(float(value)) or value <= 0:
                raise ValueError(f"{name} must be positive.")

        risk = atr * self.atr_multiplier

        if side == "BUY":
            sl = entry_price - risk
            tp = entry_price + risk * self.target_rr
        else:
            sl = entry_price + risk
            tp = entry_price - risk * self.target_rr

        rr = abs(tp - entry_price) / abs(entry_price - sl)

        approved = rr >= self.minimum_rr

        return ExitPlan(
            approved=approved,
            reason="Approved" if approved else "Risk/Reward below minimum.",
            side=side,
            entry_price=round(entry_price, 8),
            stop_loss=round(sl, 8),
            take_profit=round(tp, 8),
            risk_reward=round(rr, 2),
            atr=round(atr, 8),
        )


if __name__ == "__main__":
    engine = StopLossTakeProfitEngine()
    print(engine.calculate(side="BUY", entry_price=60000, atr=400).as_dict())