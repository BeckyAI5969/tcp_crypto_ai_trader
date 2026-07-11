from dataclasses import dataclass
from typing import Any

from src.paper_trader import PaperTrader


@dataclass
class ExecutionResult:
    success: bool
    mode: str
    action: str
    symbol: str
    message: str
    position: Any = None


class ExecutionRouter:

    PAPER_MODE = "PAPER"
    TESTNET_MODE = "TESTNET"

    def __init__(
        self,
        mode: str = PAPER_MODE,
        paper_trader: PaperTrader | None = None,
    ):
        self.mode = mode.upper()
        self.paper_trader = paper_trader or PaperTrader()

        if self.mode not in {
            self.PAPER_MODE,
            self.TESTNET_MODE,
        }:
            raise ValueError(
                "Execution mode must be PAPER or TESTNET"
            )

    def execute_entry(
        self,
        symbol: str,
        side: str,
        price: float,
        score: float,
        atr: float,
    ) -> ExecutionResult:

        symbol = symbol.upper()
        side = side.upper()

        if side not in {"BUY", "SELL"}:
            return ExecutionResult(
                success=False,
                mode=self.mode,
                action="REJECT",
                symbol=symbol,
                message="Invalid execution side",
            )

        if self.mode == self.PAPER_MODE:
            position = self.paper_trader.on_signal(
                symbol=symbol,
                signal=side,
                price=price,
                score=score,
                atr=atr,
            )

            if position is None:
                return ExecutionResult(
                    success=False,
                    mode=self.mode,
                    action="REJECT",
                    symbol=symbol,
                    message="Paper trade rejected",
                )

            return ExecutionResult(
                success=True,
                mode=self.mode,
                action="OPEN",
                symbol=symbol,
                message="Paper position opened",
                position=position,
            )

        return ExecutionResult(
            success=False,
            mode=self.mode,
            action="NOT_IMPLEMENTED",
            symbol=symbol,
            message="Binance Testnet execution is not enabled yet",
        )

    def update_position(
        self,
        symbol: str,
        price: float,
    ) -> ExecutionResult:

        symbol = symbol.upper()

        if self.mode == self.PAPER_MODE:
            position = self.paper_trader.update_market_price(
                symbol=symbol,
                price=price,
            )

            if position is None:
                return ExecutionResult(
                    success=True,
                    mode=self.mode,
                    action="NO_POSITION",
                    symbol=symbol,
                    message="No open position",
                )

            if position.is_open():
                return ExecutionResult(
                    success=True,
                    mode=self.mode,
                    action="UPDATE",
                    symbol=symbol,
                    message="Paper position updated",
                    position=position,
                )

            return ExecutionResult(
                success=True,
                mode=self.mode,
                action="CLOSE",
                symbol=symbol,
                message=(
                    "Paper position closed: "
                    f"{position.exit_reason}"
                ),
                position=position,
            )

        return ExecutionResult(
            success=False,
            mode=self.mode,
            action="NOT_IMPLEMENTED",
            symbol=symbol,
            message="Binance Testnet position update is not enabled yet",
        )

    def close_position(
        self,
        symbol: str,
        price: float,
        reason: str = "MANUAL",
    ) -> ExecutionResult:

        symbol = symbol.upper()

        if self.mode == self.PAPER_MODE:
            position = self.paper_trader.close_position(
                symbol=symbol,
                exit_price=price,
                reason=reason,
            )

            if position is None:
                return ExecutionResult(
                    success=False,
                    mode=self.mode,
                    action="NO_POSITION",
                    symbol=symbol,
                    message="No open position to close",
                )

            return ExecutionResult(
                success=True,
                mode=self.mode,
                action="CLOSE",
                symbol=symbol,
                message=f"Paper position closed: {reason}",
                position=position,
            )

        return ExecutionResult(
            success=False,
            mode=self.mode,
            action="NOT_IMPLEMENTED",
            symbol=symbol,
            message="Binance Testnet close is not enabled yet",
        )

    def has_open_position(
        self,
        symbol: str,
    ) -> bool:

        if self.mode != self.PAPER_MODE:
            return False

        position = (
            self.paper_trader
            .portfolio
            .find_open_position(symbol.upper())
        )

        return position is not None

    def portfolio_summary(self) -> dict:

        if self.mode == self.PAPER_MODE:
            return self.paper_trader.summary()

        return {}

    def risk_summary(self) -> dict:

        if self.mode == self.PAPER_MODE:
            return self.paper_trader.risk_summary()

        return {}

    def set_mode(self, mode: str):

        mode = mode.upper()

        if mode not in {
            self.PAPER_MODE,
            self.TESTNET_MODE,
        }:
            raise ValueError(
                "Execution mode must be PAPER or TESTNET"
            )

        self.mode = mode