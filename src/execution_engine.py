from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Optional

from src.signal_queue import SignalQueue, PendingSignal
from src.confirmation_engine import (
    ConfirmationEngine,
    ConfirmationResult,
)
from src.entry_engine import EntryEngine, EntryDecision
from src.execution_router import ExecutionRouter, ExecutionResult


@dataclass
class ExecutionEvent:
    timestamp: str
    symbol: str
    stage: str
    action: str
    success: bool
    message: str
    details: dict

    def to_dict(self) -> dict:
        return asdict(self)


class ExecutionEngine:

    def __init__(
        self,
        execution_mode: str = ExecutionRouter.PAPER_MODE,
        signal_validity_minutes: int = 15,
    ):
        self.signal_queue = SignalQueue(
            validity_minutes=signal_validity_minutes
        )

        self.confirmation_engine = ConfirmationEngine()
        self.entry_engine = EntryEngine()

        self.router = ExecutionRouter(
            mode=execution_mode
        )

        self.events: list[ExecutionEvent] = []

    def on_15m_signal(
        self,
        symbol: str,
        signal: str,
        score: float,
        signal_price: float,
        atr: float,
        created_at: Optional[datetime] = None,
    ) -> ExecutionEvent:

        symbol = symbol.upper()
        signal = signal.upper()

        if signal not in {"BUY", "SELL"}:
            return self._record_event(
                symbol=symbol,
                stage="15M_SIGNAL",
                action="IGNORE",
                success=True,
                message="Signal is WAIT",
                details={
                    "signal": signal,
                    "score": score,
                    "price": signal_price,
                    "atr": atr,
                },
            )

        if self.router.has_open_position(symbol):
            return self._record_event(
                symbol=symbol,
                stage="15M_SIGNAL",
                action="REJECT",
                success=False,
                message="Open position already exists",
                details={
                    "signal": signal,
                    "score": score,
                    "price": signal_price,
                    "atr": atr,
                },
            )

        pending_signal = self.signal_queue.add(
            symbol=symbol,
            side=signal,
            score=score,
            signal_price=signal_price,
            atr=atr,
            created_at=created_at,
        )

        return self._record_event(
            symbol=symbol,
            stage="15M_SIGNAL",
            action="QUEUE",
            success=True,
            message="15m signal added to queue",
            details=pending_signal.to_dict(),
        )

    def on_5m_close(
        self,
        symbol: str,
        ema20: float,
        ema50: float,
        macd: float,
        macd_signal: float,
        rsi14: float,
        volume: float,
        volume_ma20: float,
        timestamp: Optional[datetime] = None,
    ) -> ExecutionEvent:

        symbol = symbol.upper()
        timestamp = timestamp or datetime.now()

        pending_signal = self._get_valid_signal(
            symbol=symbol,
            now=timestamp,
            required_status="PENDING",
        )

        if pending_signal is None:
            return self._record_event(
                symbol=symbol,
                stage="5M_CONFIRMATION",
                action="SKIP",
                success=False,
                message="No active pending signal",
                details={},
            )

        result: ConfirmationResult = (
            self.confirmation_engine.confirm(
                side=pending_signal.side,
                ema20=ema20,
                ema50=ema50,
                macd=macd,
                macd_signal=macd_signal,
                rsi14=rsi14,
                volume=volume,
                volume_ma20=volume_ma20,
            )
        )

        details = {
            "confirmation_score": result.score,
            "confirmation_reason": result.reason,
            "signal": pending_signal.to_dict(),
        }

        if result.approved:
            pending_signal.confirm()

            return self._record_event(
                symbol=symbol,
                stage="5M_CONFIRMATION",
                action="CONFIRM",
                success=True,
                message="5m confirmation passed",
                details=details,
            )

        return self._record_event(
            symbol=symbol,
            stage="5M_CONFIRMATION",
            action="WAIT",
            success=False,
            message="5m confirmation not passed yet",
            details=details,
        )

    def on_1m_close(
        self,
        symbol: str,
        current_price: float,
        ema20: float,
        ema50: float,
        rsi14: float,
        macd: float,
        macd_signal: float,
        timestamp: Optional[datetime] = None,
    ) -> ExecutionEvent:

        symbol = symbol.upper()
        timestamp = timestamp or datetime.now()

        confirmed_signal = self._get_valid_signal(
            symbol=symbol,
            now=timestamp,
            required_status="CONFIRMED",
        )

        if confirmed_signal is None:
            return self._record_event(
                symbol=symbol,
                stage="1M_ENTRY",
                action="SKIP",
                success=False,
                message="No confirmed signal available",
                details={},
            )

        entry: EntryDecision = self.entry_engine.evaluate(
            side=confirmed_signal.side,
            current_price=current_price,
            ema20=ema20,
            ema50=ema50,
            rsi14=rsi14,
            macd=macd,
            macd_signal=macd_signal,
        )

        entry_details = {
            "entry_approved": entry.approved,
            "entry_price": entry.entry_price,
            "entry_score": entry.entry_score,
            "entry_reason": entry.reason,
            "signal": confirmed_signal.to_dict(),
        }

        if not entry.approved:
            return self._record_event(
                symbol=symbol,
                stage="1M_ENTRY",
                action="WAIT",
                success=False,
                message="1m entry conditions not passed yet",
                details=entry_details,
            )

        execution: ExecutionResult = self.router.execute_entry(
            symbol=symbol,
            side=confirmed_signal.side,
            price=entry.entry_price,
            score=confirmed_signal.score,
            atr=confirmed_signal.atr,
        )

        if execution.success:
            confirmed_signal.execute()

            position_data = (
                execution.position.to_dict()
                if execution.position is not None
                else None
            )

            return self._record_event(
                symbol=symbol,
                stage="1M_ENTRY",
                action="EXECUTE",
                success=True,
                message=execution.message,
                details={
                    **entry_details,
                    "position": position_data,
                },
            )

        confirmed_signal.reject(execution.message)

        return self._record_event(
            symbol=symbol,
            stage="1M_ENTRY",
            action="REJECT",
            success=False,
            message=execution.message,
            details=entry_details,
        )

    def on_tick(
        self,
        symbol: str,
        price: float,
    ) -> ExecutionEvent:

        symbol = symbol.upper()

        result: ExecutionResult = self.router.update_position(
            symbol=symbol,
            price=price,
        )

        position_data: Any = None

        if result.position is not None:
            position_data = result.position.to_dict()

        return self._record_event(
            symbol=symbol,
            stage="TICK_POSITION_MANAGEMENT",
            action=result.action,
            success=result.success,
            message=result.message,
            details={
                "price": price,
                "position": position_data,
            },
        )

    def close_position(
        self,
        symbol: str,
        price: float,
        reason: str = "MANUAL",
    ) -> ExecutionEvent:

        symbol = symbol.upper()

        result = self.router.close_position(
            symbol=symbol,
            price=price,
            reason=reason,
        )

        position_data = (
            result.position.to_dict()
            if result.position is not None
            else None
        )

        return self._record_event(
            symbol=symbol,
            stage="MANUAL_CLOSE",
            action=result.action,
            success=result.success,
            message=result.message,
            details={
                "price": price,
                "reason": reason,
                "position": position_data,
            },
        )

    def expire_signals(
        self,
        now: Optional[datetime] = None,
    ) -> list[ExecutionEvent]:

        now = now or datetime.now()
        events = []

        for signal in self.signal_queue.signals.values():
            if (
                signal.status in {"PENDING", "CONFIRMED"}
                and signal.is_expired(now)
            ):
                signal.expire()

                events.append(
                    self._record_event(
                        symbol=signal.symbol,
                        stage="SIGNAL_QUEUE",
                        action="EXPIRE",
                        success=True,
                        message="Signal expired",
                        details=signal.to_dict(),
                    )
                )

        return events

    def clear_inactive_signals(self):
        inactive_symbols = [
            symbol
            for symbol, signal
            in self.signal_queue.signals.items()
            if signal.status
            in {"EXECUTED", "REJECTED", "EXPIRED"}
        ]

        for symbol in inactive_symbols:
            self.signal_queue.remove(symbol)

    def get_signal(
        self,
        symbol: str,
    ) -> Optional[PendingSignal]:

        return self.signal_queue.get(symbol.upper())

    def portfolio_summary(self) -> dict:
        return self.router.portfolio_summary()

    def risk_summary(self) -> dict:
        return self.router.risk_summary()

    def summary(self) -> dict:
        return {
            "execution_mode": self.router.mode,
            "signal_queue": self.signal_queue.summary(),
            "portfolio": self.portfolio_summary(),
            "risk": self.risk_summary(),
            "event_count": len(self.events),
        }

    def _get_valid_signal(
        self,
        symbol: str,
        now: datetime,
        required_status: str,
    ) -> Optional[PendingSignal]:

        signal = self.signal_queue.get(symbol, now)

        if signal is None:
            return None

        if signal.is_expired(now):
            signal.expire()
            return None

        if signal.status != required_status:
            return None

        return signal

    def _record_event(
        self,
        symbol: str,
        stage: str,
        action: str,
        success: bool,
        message: str,
        details: dict,
    ) -> ExecutionEvent:

        event = ExecutionEvent(
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            stage=stage,
            action=action,
            success=success,
            message=message,
            details=details,
        )

        self.events.append(event)
        return event