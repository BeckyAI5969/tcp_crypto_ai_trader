from dataclasses import dataclass
from datetime import datetime, timedelta

from src.leverage_config import DEFAULT_LEVERAGE_CONFIG
from src.position_sizer import PositionSizer


@dataclass(frozen=True)
class RiskDecision:
    approved: bool
    reason: str

    quantity: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0

    leverage: int = 0
    required_margin: float = 0.0
    risk_amount: float = 0.0
    notional_value: float = 0.0

    projected_margin_used: float = 0.0
    projected_margin_usage_pct: float = 0.0
    projected_open_risk: float = 0.0
    projected_open_risk_pct: float = 0.0


class RiskManager:

    def __init__(
        self,
        config=DEFAULT_LEVERAGE_CONFIG,
        min_strategy_score: float = 70.0,
        atr_multiplier: float = 2.0,
        risk_reward_ratio: float = 2.0,
        max_consecutive_losses: int = 3,
        cooldown_minutes: int = 60,
    ):
        self.config = config
        self.position_sizer = PositionSizer(config)

        self.min_strategy_score = min_strategy_score
        self.atr_multiplier = atr_multiplier
        self.risk_reward_ratio = risk_reward_ratio
        self.max_consecutive_losses = max_consecutive_losses
        self.cooldown_minutes = cooldown_minutes

        self.daily_realized_pnl = 0.0
        self.consecutive_losses = 0
        self.cooldown_until = None

    def evaluate(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        atr: float,
        strategy_score: float,
        portfolio_summary: dict,
    ) -> RiskDecision:

        symbol = symbol.upper()
        side = side.upper()

        if side not in {"BUY", "SELL"}:
            return self._reject("Invalid side")

        if entry_price <= 0:
            return self._reject("Invalid entry price")

        if atr <= 0:
            return self._reject("ATR is invalid or zero")

        if strategy_score < self.min_strategy_score:
            return self._reject(
                "Strategy score below minimum "
                f"({strategy_score} < {self.min_strategy_score})"
            )

        if (
            self.cooldown_until is not None
            and datetime.now() < self.cooldown_until
        ):
            return self._reject("Cooldown active")

        if (
            self.daily_realized_pnl
            <= -self.config.maximum_daily_loss_amount()
        ):
            return self._reject("Daily loss limit reached")

        open_positions = int(
            portfolio_summary.get("open_positions", 0)
        )

        if open_positions >= self.config.max_open_positions:
            return self._reject(
                "Maximum open positions reached"
            )

        equity = float(
            portfolio_summary.get(
                "equity",
                self.config.initial_capital,
            )
        )

        if equity <= 0:
            return self._reject(
                "Portfolio equity is not positive"
            )

        stop_distance = max(
            atr * self.atr_multiplier,
            entry_price * 0.002,
        )

        if side == "BUY":
            stop_loss = entry_price - stop_distance
            take_profit = (
                entry_price
                + stop_distance * self.risk_reward_ratio
            )
        else:
            stop_loss = entry_price + stop_distance
            take_profit = (
                entry_price
                - stop_distance * self.risk_reward_ratio
            )

        sizing = self.position_sizer.calculate(
            symbol=symbol,
            entry_price=entry_price,
            stop_price=stop_loss,
            available_equity=equity,
            strategy_score=strategy_score,
        )

        if not sizing.approved:
            return self._reject(sizing.reason)

        current_margin_used = float(
            portfolio_summary.get("margin_used", 0.0)
        )

        current_open_risk = float(
            portfolio_summary.get("open_risk", 0.0)
        )

        projected_margin_used = (
            current_margin_used
            + sizing.required_margin
        )

        projected_open_risk = (
            current_open_risk
            + sizing.risk_amount
        )

        projected_margin_usage_pct = (
            projected_margin_used / equity
        )

        projected_open_risk_pct = (
            projected_open_risk / equity
        )

        if (
            projected_margin_usage_pct
            > self.config.max_margin_usage_pct
        ):
            return self._reject(
                "Maximum portfolio margin usage exceeded",
                projected_margin_used,
                projected_margin_usage_pct,
                projected_open_risk,
                projected_open_risk_pct,
            )

        if (
            projected_open_risk_pct
            > self.config.max_combined_open_risk_pct
        ):
            return self._reject(
                "Maximum combined open risk exceeded",
                projected_margin_used,
                projected_margin_usage_pct,
                projected_open_risk,
                projected_open_risk_pct,
            )

        minimum_reserve = (
            equity
            * self.config.minimum_cash_reserve_pct
        )

        projected_free_margin = (
            equity - projected_margin_used
        )

        if projected_free_margin < minimum_reserve:
            return self._reject(
                "Minimum cash reserve would be violated",
                projected_margin_used,
                projected_margin_usage_pct,
                projected_open_risk,
                projected_open_risk_pct,
            )

        return RiskDecision(
            approved=True,
            reason="Risk approved",
            quantity=sizing.quantity,
            stop_loss=round(stop_loss, 8),
            take_profit=round(take_profit, 8),
            leverage=sizing.leverage,
            required_margin=sizing.required_margin,
            risk_amount=sizing.risk_amount,
            notional_value=sizing.notional_value,
            projected_margin_used=round(
                projected_margin_used,
                8,
            ),
            projected_margin_usage_pct=round(
                projected_margin_usage_pct,
                8,
            ),
            projected_open_risk=round(
                projected_open_risk,
                8,
            ),
            projected_open_risk_pct=round(
                projected_open_risk_pct,
                8,
            ),
        )

    def update_after_close(self, realized_pnl: float):
        self.daily_realized_pnl += float(realized_pnl)

        if realized_pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        if (
            self.consecutive_losses
            >= self.max_consecutive_losses
        ):
            self.cooldown_until = (
                datetime.now()
                + timedelta(
                    minutes=self.cooldown_minutes
                )
            )

    def reset_daily_state(self):
        self.daily_realized_pnl = 0.0
        self.consecutive_losses = 0
        self.cooldown_until = None

    def summary(self):
        return {
            "daily_realized_pnl": round(
                self.daily_realized_pnl,
                8,
            ),
            "daily_loss_limit":
                self.config.maximum_daily_loss_amount(),
            "consecutive_losses":
                self.consecutive_losses,
            "max_consecutive_losses":
                self.max_consecutive_losses,
            "cooldown_until": (
                self.cooldown_until.isoformat()
                if self.cooldown_until
                else None
            ),
            "min_strategy_score":
                self.min_strategy_score,
            "atr_multiplier":
                self.atr_multiplier,
            "risk_reward_ratio":
                self.risk_reward_ratio,
        }

    @staticmethod
    def _reject(
        reason: str,
        projected_margin_used: float = 0.0,
        projected_margin_usage_pct: float = 0.0,
        projected_open_risk: float = 0.0,
        projected_open_risk_pct: float = 0.0,
    ) -> RiskDecision:

        return RiskDecision(
            approved=False,
            reason=reason,
            projected_margin_used=round(
                projected_margin_used,
                8,
            ),
            projected_margin_usage_pct=round(
                projected_margin_usage_pct,
                8,
            ),
            projected_open_risk=round(
                projected_open_risk,
                8,
            ),
            projected_open_risk_pct=round(
                projected_open_risk_pct,
                8,
            ),
        )