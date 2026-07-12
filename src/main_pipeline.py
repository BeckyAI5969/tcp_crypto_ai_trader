"""Main orchestration pipeline for TCP Crypto AI Trader.

This module connects the risk and paper-execution components created in
Sprints 17-18. It does not connect to Binance and does not place real orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dynamic_leverage_engine import DynamicLeverageEngine
from order_builder import OrderBuilder
from paper_execution_engine import PaperExecutionEngine
from position_size_calculator import PositionSizeCalculator
from stop_loss_take_profit_engine import StopLossTakeProfitEngine
from trade_execution_engine import (
    TradeExecutionEngine,
    TradeExecutionInput,
)


@dataclass(frozen=True)
class PipelineContext:
    symbol: str
    side: str
    confidence: float

    account_balance: float
    free_margin: float
    risk_pct: float

    entry_price: float
    atr: float
    volatility_pct: float
    current_margin_usage_pct: float = 0.0

    decision_approved: bool = True
    risk_approved: bool = True


@dataclass(frozen=True)
class MainPipelineResult:
    success: bool
    stage: str
    reason: str
    data: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "stage": self.stage,
            "reason": self.reason,
            "data": self.data,
        }


class MainPipeline:
    """Run the complete paper-trading preparation flow."""

    def __init__(self) -> None:
        self.leverage_engine = DynamicLeverageEngine()
        self.exit_engine = StopLossTakeProfitEngine()
        self.position_calculator = PositionSizeCalculator()
        self.execution_planner = TradeExecutionEngine()
        self.order_builder = OrderBuilder()
        self.paper_execution_engine = PaperExecutionEngine()

    def run(self, context: PipelineContext) -> MainPipelineResult:
        side = context.side.upper()

        if side not in {"BUY", "SELL"}:
            return self._failed(
                stage="INPUT_VALIDATION",
                reason="side must be BUY or SELL.",
            )

        if not context.decision_approved:
            return self._failed(
                stage="AI_DECISION",
                reason="AI decision was not approved.",
            )

        if not context.risk_approved:
            return self._failed(
                stage="RISK_VALIDATION",
                reason="Risk validation was not approved.",
            )

        leverage = self.leverage_engine.evaluate(
            symbol=context.symbol,
            confidence=context.confidence,
            volatility_pct=context.volatility_pct,
            margin_usage_pct=context.current_margin_usage_pct,
        )

        if not leverage.approved:
            return self._failed(
                stage="DYNAMIC_LEVERAGE",
                reason=leverage.reason,
                data={"leverage": leverage.as_dict()},
            )

        exit_plan = self.exit_engine.calculate(
            side=side,
            entry_price=context.entry_price,
            atr=context.atr,
        )

        if not exit_plan.approved:
            return self._failed(
                stage="EXIT_PLAN",
                reason=exit_plan.reason,
                data={"exit_plan": exit_plan.as_dict()},
            )

        position = self.position_calculator.calculate(
            account_balance=context.account_balance,
            free_margin=context.free_margin,
            risk_pct=context.risk_pct,
            entry_price=context.entry_price,
            stop_loss=exit_plan.stop_loss,
            leverage=leverage.leverage,
        )

        if not position.approved:
            return self._failed(
                stage="POSITION_SIZING",
                reason=position.reason,
                data={"position": position.as_dict()},
            )

        execution_input = TradeExecutionInput(
            symbol=context.symbol,
            side=side,
            confidence=context.confidence,
            entry_price=context.entry_price,
            quantity=position.quantity,
            notional_value=position.notional_value,
            required_margin=position.required_margin,
            leverage=leverage.leverage,
            stop_loss=exit_plan.stop_loss,
            take_profit=exit_plan.take_profit,
            risk_reward=exit_plan.risk_reward,
            risk_amount=position.risk_amount,
            risk_pct=position.risk_pct,
            decision_approved=context.decision_approved,
            risk_approved=context.risk_approved,
            leverage_approved=leverage.approved,
            position_size_approved=position.approved,
            exit_plan_approved=exit_plan.approved,
        )

        execution_plan = self.execution_planner.build_plan(
            execution_input
        )

        if not execution_plan.approved:
            return self._failed(
                stage="EXECUTION_PLAN",
                reason=execution_plan.reason,
                data={
                    "leverage": leverage.as_dict(),
                    "exit_plan": exit_plan.as_dict(),
                    "position": position.as_dict(),
                    "execution_plan": execution_plan.as_dict(),
                },
            )

        order = self.order_builder.build(
            symbol=execution_plan.symbol,
            side=execution_plan.side,
            quantity=execution_plan.quantity,
            leverage=execution_plan.leverage,
            entry_price=execution_plan.entry_price,
            stop_loss=execution_plan.stop_loss,
            take_profit=execution_plan.take_profit,
        )

        paper_trade = self.paper_execution_engine.execute(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            entry_price=order.entry_price,
            leverage=order.leverage,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit,
        )

        return MainPipelineResult(
            success=True,
            stage="COMPLETED",
            reason="Paper trade pipeline completed successfully.",
            data={
                "leverage": leverage.as_dict(),
                "exit_plan": exit_plan.as_dict(),
                "position": position.as_dict(),
                "execution_plan": execution_plan.as_dict(),
                "order": order.as_dict(),
                "paper_trade": paper_trade.as_dict(),
            },
        )

    @staticmethod
    def _failed(
        *,
        stage: str,
        reason: str,
        data: dict[str, Any] | None = None,
    ) -> MainPipelineResult:
        return MainPipelineResult(
            success=False,
            stage=stage,
            reason=reason,
            data=data or {},
        )


if __name__ == "__main__":
    pipeline = MainPipeline()

    sample = PipelineContext(
        symbol="BTCUSDT",
        side="BUY",
        confidence=91.0,
        account_balance=1000.0,
        free_margin=1000.0,
        risk_pct=0.02,
        entry_price=60000.0,
        atr=400.0,
        volatility_pct=0.012,
        current_margin_usage_pct=0.10,
        decision_approved=True,
        risk_approved=True,
    )

    result = pipeline.run(sample)
    print(result.as_dict())