from dataclasses import dataclass, field


@dataclass(frozen=True)
class LeverageConfig:
    initial_capital: float = 1000.0

    margin_mode: str = "ISOLATED"

    symbol_leverage: dict[str, int] = field(
        default_factory=lambda: {
            "BTCUSDT": 10,
            "ETHUSDT": 5,
            "SOLUSDT": 5,
            "XRPUSDT": 5,
            "BNBUSDT": 5,
        }
    )

    max_allowed_leverage: int = 10

    max_margin_usage_pct: float = 0.60
    minimum_cash_reserve_pct: float = 0.40

    base_risk_per_trade: float = 0.01
    max_risk_per_trade: float = 0.0125
    max_daily_loss_pct: float = 0.03
    max_combined_open_risk_pct: float = 0.025

    max_open_positions: int = 3

    liquidation_buffer_multiple: float = 3.0

    include_trading_fee: bool = True
    include_slippage: bool = True
    include_funding_fee: bool = True

    taker_fee_rate: float = 0.0005
    maker_fee_rate: float = 0.0002
    estimated_slippage_rate: float = 0.0003

    def __post_init__(self):
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be greater than zero")

        if self.margin_mode.upper() != "ISOLATED":
            raise ValueError("Only ISOLATED margin mode is allowed")

        if not 0 < self.max_margin_usage_pct <= 1:
            raise ValueError(
                "max_margin_usage_pct must be between 0 and 1"
            )

        if not 0 <= self.minimum_cash_reserve_pct < 1:
            raise ValueError(
                "minimum_cash_reserve_pct must be between 0 and 1"
            )

        if (
            self.max_margin_usage_pct
            + self.minimum_cash_reserve_pct
            > 1
        ):
            raise ValueError(
                "margin usage plus cash reserve cannot exceed 100%"
            )

        if not 0 < self.base_risk_per_trade <= 1:
            raise ValueError(
                "base_risk_per_trade must be between 0 and 1"
            )

        if not 0 < self.max_risk_per_trade <= 1:
            raise ValueError(
                "max_risk_per_trade must be between 0 and 1"
            )

        if self.max_risk_per_trade < self.base_risk_per_trade:
            raise ValueError(
                "max_risk_per_trade cannot be below base risk"
            )

        if not 0 < self.max_daily_loss_pct <= 1:
            raise ValueError(
                "max_daily_loss_pct must be between 0 and 1"
            )

        if not 0 < self.max_combined_open_risk_pct <= 1:
            raise ValueError(
                "max_combined_open_risk_pct must be between 0 and 1"
            )

        if self.max_open_positions <= 0:
            raise ValueError(
                "max_open_positions must be greater than zero"
            )

        if self.max_allowed_leverage <= 0:
            raise ValueError(
                "max_allowed_leverage must be greater than zero"
            )

        if self.liquidation_buffer_multiple < 1:
            raise ValueError(
                "liquidation_buffer_multiple must be at least 1"
            )

        for symbol, leverage in self.symbol_leverage.items():
            if not symbol:
                raise ValueError("symbol cannot be empty")

            if leverage <= 0:
                raise ValueError(
                    f"leverage for {symbol} must be greater than zero"
                )

            if leverage > self.max_allowed_leverage:
                raise ValueError(
                    f"leverage for {symbol} exceeds "
                    f"max_allowed_leverage"
                )

    def get_leverage(self, symbol: str) -> int:
        normalized_symbol = symbol.upper()

        if normalized_symbol not in self.symbol_leverage:
            raise KeyError(
                f"No leverage configured for {normalized_symbol}"
            )

        return self.symbol_leverage[normalized_symbol]

    def maximum_margin_amount(self) -> float:
        return round(
            self.initial_capital * self.max_margin_usage_pct,
            8,
        )

    def minimum_cash_reserve_amount(self) -> float:
        return round(
            self.initial_capital * self.minimum_cash_reserve_pct,
            8,
        )

    def maximum_daily_loss_amount(self) -> float:
        return round(
            self.initial_capital * self.max_daily_loss_pct,
            8,
        )

    def maximum_combined_open_risk_amount(self) -> float:
        return round(
            self.initial_capital
            * self.max_combined_open_risk_pct,
            8,
        )

    def base_risk_amount(self) -> float:
        return round(
            self.initial_capital * self.base_risk_per_trade,
            8,
        )

    def maximum_risk_amount(self) -> float:
        return round(
            self.initial_capital * self.max_risk_per_trade,
            8,
        )

    def summary(self) -> dict:
        return {
            "initial_capital": self.initial_capital,
            "margin_mode": self.margin_mode.upper(),
            "symbol_leverage": dict(self.symbol_leverage),
            "max_allowed_leverage": self.max_allowed_leverage,
            "max_margin_usage_pct": self.max_margin_usage_pct,
            "maximum_margin_amount":
                self.maximum_margin_amount(),
            "minimum_cash_reserve_pct":
                self.minimum_cash_reserve_pct,
            "minimum_cash_reserve_amount":
                self.minimum_cash_reserve_amount(),
            "base_risk_per_trade":
                self.base_risk_per_trade,
            "base_risk_amount":
                self.base_risk_amount(),
            "max_risk_per_trade":
                self.max_risk_per_trade,
            "maximum_risk_amount":
                self.maximum_risk_amount(),
            "max_daily_loss_pct":
                self.max_daily_loss_pct,
            "maximum_daily_loss_amount":
                self.maximum_daily_loss_amount(),
            "max_combined_open_risk_pct":
                self.max_combined_open_risk_pct,
            "maximum_combined_open_risk_amount":
                self.maximum_combined_open_risk_amount(),
            "max_open_positions":
                self.max_open_positions,
            "liquidation_buffer_multiple":
                self.liquidation_buffer_multiple,
            "include_trading_fee":
                self.include_trading_fee,
            "include_slippage":
                self.include_slippage,
            "include_funding_fee":
                self.include_funding_fee,
            "taker_fee_rate":
                self.taker_fee_rate,
            "maker_fee_rate":
                self.maker_fee_rate,
            "estimated_slippage_rate":
                self.estimated_slippage_rate,
        }


DEFAULT_LEVERAGE_CONFIG = LeverageConfig()