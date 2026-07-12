"""Trade Pipeline for TCP Crypto AI Trader."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PipelineResult:
    success: bool
    stage: str
    data: dict[str, Any]


class TradePipeline:

    def __init__(
        self,
        decision_engine,
        risk_validator,
        position_engine,
        leverage_engine,
        sltp_engine,
        order_builder,
        execution_engine,
    ):
        self.decision_engine = decision_engine
        self.risk_validator = risk_validator
        self.position_engine = position_engine
        self.leverage_engine = leverage_engine
        self.sltp_engine = sltp_engine
        self.order_builder = order_builder
        self.execution_engine = execution_engine

    def run(self, context):

        decision = self.decision_engine(context)

        if not decision:
            return PipelineResult(False, "AI Decision", {})

        risk = self.risk_validator(context)

        if not risk:
            return PipelineResult(False, "Risk Validation", {})

        position = self.position_engine(context)

        leverage = self.leverage_engine(context)

        sltp = self.sltp_engine(context)

        order = self.order_builder(
            context,
            position,
            leverage,
            sltp,
        )

        execution = self.execution_engine(order)

        return PipelineResult(
            success=True,
            stage="Completed",
            data={
                "decision": decision,
                "risk": risk,
                "position": position,
                "leverage": leverage,
                "stop_loss_take_profit": sltp,
                "order": order,
                "execution": execution,
            },
        )