from dataclasses import dataclass
from typing import Dict


@dataclass
class PortfolioConfig:
    initial_capital: float = 100000.0
    risk_per_trade: float = 0.01
    max_position_per_symbol: float = 0.20
    max_total_exposure: float = 0.80
    allocation_mode: str = "equal_weight"


@dataclass
class Position:
    symbol: str
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    capital_used: float
    risk_amount: float


class CapitalManager:
    def __init__(self, initial_capital: float):
        self.initial_capital = float(initial_capital)
        self.cash = float(initial_capital)
        self.realized_pnl = 0.0

    def allocate(self, amount: float) -> bool:
        if amount <= self.cash:
            self.cash -= amount
            return True
        return False

    def release(self, amount: float, pnl: float = 0.0):
        self.cash += amount + pnl
        self.realized_pnl += pnl

    def equity(self, unrealized_pnl: float = 0.0) -> float:
        return self.cash + unrealized_pnl


class AllocationEngine:
    def __init__(self, symbols, config: PortfolioConfig):
        self.symbols = symbols
        self.config = config

    def equal_weight(self) -> Dict[str, float]:
        if not self.symbols:
            return {}

        weight = 1 / len(self.symbols)

        return {
            symbol: min(weight, self.config.max_position_per_symbol)
            for symbol in self.symbols
        }


class PositionSizer:
    def __init__(self, config: PortfolioConfig):
        self.config = config

    def calculate_quantity(
        self,
        equity: float,
        entry_price: float,
        stop_loss: float,
    ) -> float:
        risk_amount = equity * self.config.risk_per_trade
        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit <= 0:
            return 0.0

        quantity = risk_amount / risk_per_unit
        max_position_value = equity * self.config.max_position_per_symbol
        max_quantity = max_position_value / entry_price

        return round(min(quantity, max_quantity), 6)

    def capital_used(self, quantity: float, entry_price: float) -> float:
        return round(quantity * entry_price, 4)

    def risk_amount(
        self,
        quantity: float,
        entry_price: float,
        stop_loss: float,
    ) -> float:
        return round(abs(entry_price - stop_loss) * quantity, 4)