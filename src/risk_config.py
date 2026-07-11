from dataclasses import dataclass


@dataclass(frozen=True)
class RiskConfig:
    initial_balance: float = 10000.0

    base_risk_per_trade: float = 0.01
    min_risk_per_trade: float = 0.0025
    max_risk_per_trade: float = 0.0125

    max_daily_loss_pct: float = 0.03
    soft_daily_profit_target: float = 300.0
    hard_daily_profit_target: float = 500.0

    max_open_positions: int = 5
    max_portfolio_exposure_pct: float = 0.35
    max_symbol_exposure_pct: float = 0.12

    min_strategy_score: float = 70.0
    high_confidence_score: float = 90.0

    atr_multiplier: float = 2.0
    risk_reward_ratio: float = 2.0

    max_consecutive_losses: int = 3
    cooldown_minutes: int = 120

    reduce_risk_after_soft_target: bool = True
    stop_trading_after_hard_target: bool = True

    aggressive_mode: bool = False


DEFAULT_RISK_CONFIG = RiskConfig()