from dataclasses import dataclass
from typing import Dict, List

import pandas as pd

from src.portfolio_models import (
    CapitalManager,
    AllocationEngine,
    PortfolioConfig,
)


@dataclass
class PortfolioTrade:
    symbol: str
    entry_time: str
    exit_time: str
    profit: float
    capital: float


class PortfolioBacktestEngine:

    def __init__(self):

        self.config = PortfolioConfig()

        self.capital = CapitalManager(
            self.config.initial_capital
        )

        self.symbols = [
            "BTCUSDT",
            "ETHUSDT",
            "SOLUSDT",
            "XRPUSDT",
            "BNBUSDT",
        ]

        self.allocation = AllocationEngine(
            self.symbols,
            self.config,
        )

        self.portfolio_history = []

        self.trade_history = []

    def current_equity(self):

        return self.capital.equity()

    def current_cash(self):

        return self.capital.cash

    def weights(self):

        return self.allocation.equal_weight()

    def add_trade(
        self,
        symbol,
        profit,
        capital,
        entry_time="",
        exit_time="",
    ):

        trade = PortfolioTrade(
            symbol=symbol,
            entry_time=entry_time,
            exit_time=exit_time,
            profit=profit,
            capital=capital,
        )

        self.trade_history.append(trade)

    def record_equity(self):

        self.portfolio_history.append(
            {
                "equity": self.current_equity(),
                "cash": self.current_cash(),
            }
        )

    def trade_dataframe(self):

        return pd.DataFrame(
            [
                t.__dict__
                for t in self.trade_history
            ]
        )

    def equity_dataframe(self):

        return pd.DataFrame(
            self.portfolio_history
        )