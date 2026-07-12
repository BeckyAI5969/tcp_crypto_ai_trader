from dataclasses import dataclass


@dataclass(frozen=True)
class PositionPlan:
    approved: bool
    reason: str

    position_size_pct: float
    leverage: int

    stop_loss: float
    take_profit: float

    risk_reward: float

    expected_loss: float
    expected_profit: float


class RiskPositionEngine:

    def __init__(
        self,
        max_risk_pct=0.02,
        minimum_rr=2.0,
    ):
        self.max_risk_pct = max_risk_pct
        self.minimum_rr = minimum_rr

    def evaluate(
        self,
        account_balance,
        confidence,
        atr,
        entry_price,
    ):
        pass