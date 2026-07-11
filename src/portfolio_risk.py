from dataclasses import dataclass

from src.leverage_config import DEFAULT_LEVERAGE_CONFIG


@dataclass(frozen=True)
class PortfolioRiskSnapshot:
    capital: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    open_positions: int

    margin_used: float
    free_margin: float
    margin_usage_pct: float

    open_risk: float
    open_risk_pct: float

    max_margin_allowed: float
    max_open_risk_allowed: float


@dataclass(frozen=True)
class PortfolioRiskDecision:
    approved: bool
    reason: str

    projected_margin_used: float
    projected_margin_usage_pct: float

    projected_open_risk: float
    projected_open_risk_pct: float

    remaining_margin: float
    remaining_risk_budget: float


class PortfolioRiskEngine:

    def __init__(self, config=DEFAULT_LEVERAGE_CONFIG):
        self.config = config

    def snapshot(self, portfolio) -> PortfolioRiskSnapshot:
        capital = float(self.config.initial_capital)
        realized_pnl = float(portfolio.total_realized_pnl())
        unrealized_pnl = float(portfolio.total_unrealized_pnl())

        equity = capital + realized_pnl + unrealized_pnl
        equity = max(equity, 0.0)

        open_positions = portfolio.get_open_positions()

        margin_used = round(
            sum(
                float(getattr(position, "required_margin", 0.0))
                for position in open_positions
            ),
            8,
        )

        open_risk = round(
            sum(
                float(getattr(position, "risk_amount", 0.0))
                for position in open_positions
            ),
            8,
        )

        free_margin = round(
            max(equity - margin_used, 0.0),
            8,
        )

        margin_usage_pct = (
            margin_used / equity
            if equity > 0
            else 1.0
        )

        open_risk_pct = (
            open_risk / equity
            if equity > 0
            else 1.0
        )

        max_margin_allowed = (
            equity * self.config.max_margin_usage_pct
        )

        max_open_risk_allowed = (
            equity * self.config.max_combined_open_risk_pct
        )

        return PortfolioRiskSnapshot(
            capital=round(capital, 8),
            equity=round(equity, 8),
            realized_pnl=round(realized_pnl, 8),
            unrealized_pnl=round(unrealized_pnl, 8),
            open_positions=len(open_positions),
            margin_used=margin_used,
            free_margin=free_margin,
            margin_usage_pct=round(margin_usage_pct, 8),
            open_risk=open_risk,
            open_risk_pct=round(open_risk_pct, 8),
            max_margin_allowed=round(max_margin_allowed, 8),
            max_open_risk_allowed=round(max_open_risk_allowed, 8),
        )

    def evaluate_new_position(
        self,
        portfolio,
        required_margin: float,
        risk_amount: float,
    ) -> PortfolioRiskDecision:

        snapshot = self.snapshot(portfolio)

        projected_margin_used = round(
            snapshot.margin_used + float(required_margin),
            8,
        )

        projected_open_risk = round(
            snapshot.open_risk + float(risk_amount),
            8,
        )

        projected_margin_usage_pct = (
            projected_margin_used / snapshot.equity
            if snapshot.equity > 0
            else 1.0
        )

        projected_open_risk_pct = (
            projected_open_risk / snapshot.equity
            if snapshot.equity > 0
            else 1.0
        )

        remaining_margin = round(
            max(
                snapshot.max_margin_allowed
                - projected_margin_used,
                0.0,
            ),
            8,
        )

        remaining_risk_budget = round(
            max(
                snapshot.max_open_risk_allowed
                - projected_open_risk,
                0.0,
            ),
            8,
        )

        if (
            snapshot.open_positions
            >= self.config.max_open_positions
        ):
            return self._decision(
                False,
                "Maximum open positions reached",
                projected_margin_used,
                projected_margin_usage_pct,
                projected_open_risk,
                projected_open_risk_pct,
                remaining_margin,
                remaining_risk_budget,
            )

        if (
            projected_margin_usage_pct
            > self.config.max_margin_usage_pct
        ):
            return self._decision(
                False,
                "Maximum portfolio margin usage exceeded",
                projected_margin_used,
                projected_margin_usage_pct,
                projected_open_risk,
                projected_open_risk_pct,
                remaining_margin,
                remaining_risk_budget,
            )

        if (
            projected_open_risk_pct
            > self.config.max_combined_open_risk_pct
        ):
            return self._decision(
                False,
                "Maximum combined open risk exceeded",
                projected_margin_used,
                projected_margin_usage_pct,
                projected_open_risk,
                projected_open_risk_pct,
                remaining_margin,
                remaining_risk_budget,
            )

        minimum_reserve = (
            snapshot.equity
            * self.config.minimum_cash_reserve_pct
        )

        projected_free_margin = (
            snapshot.equity - projected_margin_used
        )

        if projected_free_margin < minimum_reserve:
            return self._decision(
                False,
                "Minimum cash reserve would be violated",
                projected_margin_used,
                projected_margin_usage_pct,
                projected_open_risk,
                projected_open_risk_pct,
                remaining_margin,
                remaining_risk_budget,
            )

        return self._decision(
            True,
            "Portfolio risk approved",
            projected_margin_used,
            projected_margin_usage_pct,
            projected_open_risk,
            projected_open_risk_pct,
            remaining_margin,
            remaining_risk_budget,
        )

    def summary(self, portfolio) -> dict:
        snapshot = self.snapshot(portfolio)

        return {
            "capital": snapshot.capital,
            "equity": snapshot.equity,
            "realized_pnl": snapshot.realized_pnl,
            "unrealized_pnl": snapshot.unrealized_pnl,
            "open_positions": snapshot.open_positions,
            "margin_used": snapshot.margin_used,
            "free_margin": snapshot.free_margin,
            "margin_usage_pct": snapshot.margin_usage_pct,
            "open_risk": snapshot.open_risk,
            "open_risk_pct": snapshot.open_risk_pct,
            "max_margin_allowed": snapshot.max_margin_allowed,
            "max_open_risk_allowed":
                snapshot.max_open_risk_allowed,
        }

    @staticmethod
    def _decision(
        approved: bool,
        reason: str,
        projected_margin_used: float,
        projected_margin_usage_pct: float,
        projected_open_risk: float,
        projected_open_risk_pct: float,
        remaining_margin: float,
        remaining_risk_budget: float,
    ) -> PortfolioRiskDecision:

        return PortfolioRiskDecision(
            approved=approved,
            reason=reason,
            projected_margin_used=round(projected_margin_used, 8),
            projected_margin_usage_pct=round(
                projected_margin_usage_pct,
                8,
            ),
            projected_open_risk=round(projected_open_risk, 8),
            projected_open_risk_pct=round(
                projected_open_risk_pct,
                8,
            ),
            remaining_margin=round(remaining_margin, 8),
            remaining_risk_budget=round(
                remaining_risk_budget,
                8,
            ),
        )