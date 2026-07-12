"""AI Decision Engine v2.

Combines AI score + multi-timeframe confirmation + risk gate into a final
decision. This module does not place orders.
"""

from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):
    BUY="BUY"
    SELL="SELL"
    WAIT="WAIT"


@dataclass(frozen=True)
class DecisionInput:
    symbol:str
    ai_score:float
    ai_confidence:float
    timeframe_decision:str
    timeframe_confidence:float
    risk_allowed:bool
    risk_reason:str=""


@dataclass(frozen=True)
class DecisionResult:
    symbol:str
    decision:Decision
    final_score:float
    confidence:float
    reasons:tuple[str,...]


class AIDecisionEngine:
    def __init__(self,buy_threshold=80.0,sell_threshold=20.0):
        self.buy_threshold=buy_threshold
        self.sell_threshold=sell_threshold

    def evaluate(self,data:DecisionInput)->DecisionResult:
        reasons=[]
        if not data.risk_allowed:
            return DecisionResult(
                data.symbol,Decision.WAIT,data.ai_score,data.ai_confidence,
                (f"Risk filter blocked trading: {data.risk_reason}",)
            )

        combined=(data.ai_score*0.7)+(data.timeframe_confidence*0.3)

        tf=data.timeframe_decision.upper()

        if tf=="BUY" and combined>=self.buy_threshold:
            decision=Decision.BUY
            reasons.append("AI score and multi-timeframe confirmation support BUY.")
        elif tf=="SELL" and combined<=self.sell_threshold:
            decision=Decision.SELL
            reasons.append("AI score and multi-timeframe confirmation support SELL.")
        else:
            decision=Decision.WAIT
            reasons.append("Conditions are not strong enough to trade.")

        reasons.append(f"AI Score: {data.ai_score:.1f}")
        reasons.append(f"Combined Score: {combined:.1f}")
        reasons.append(f"Timeframe Decision: {tf}")

        return DecisionResult(
            symbol=data.symbol,
            decision=decision,
            final_score=round(combined,2),
            confidence=round((data.ai_confidence+data.timeframe_confidence)/2,2),
            reasons=tuple(reasons),
        )


if __name__=="__main__":
    engine=AIDecisionEngine()
    sample=DecisionInput(
        symbol="BTCUSDT",
        ai_score=89,
        ai_confidence=92,
        timeframe_decision="BUY",
        timeframe_confidence=86,
        risk_allowed=True
    )
    print(engine.evaluate(sample))