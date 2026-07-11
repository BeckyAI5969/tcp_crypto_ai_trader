from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class PendingSignal:
    symbol: str
    side: str
    score: float
    signal_price: float
    atr: float
    created_at: datetime
    expires_at: datetime

    status: str = "PENDING"
    reason: str = ""

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now()
        return now >= self.expires_at

    def is_active(self, now: Optional[datetime] = None) -> bool:
        return (
            self.status == "PENDING"
            and not self.is_expired(now)
        )

    def expire(self):
        self.status = "EXPIRED"
        self.reason = "Signal validity period expired"

    def confirm(self):
        self.status = "CONFIRMED"
        self.reason = "5m confirmation passed"

    def reject(self, reason: str):
        self.status = "REJECTED"
        self.reason = reason

    def execute(self):
        self.status = "EXECUTED"
        self.reason = "Entry executed"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["expires_at"] = self.expires_at.isoformat()
        return data


class SignalQueue:

    def __init__(self, validity_minutes: int = 15):
        if validity_minutes <= 0:
            raise ValueError("validity_minutes must be greater than zero")

        self.validity_minutes = validity_minutes
        self.signals: dict[str, PendingSignal] = {}

    def add(
        self,
        symbol: str,
        side: str,
        score: float,
        signal_price: float,
        atr: float,
        created_at: Optional[datetime] = None,
    ) -> PendingSignal:

        symbol = symbol.upper()
        side = side.upper()
        created_at = created_at or datetime.now()

        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")

        existing = self.get(symbol)

        if (
            existing is not None
            and existing.is_active(created_at)
            and existing.side == side
        ):
            return existing

        signal = PendingSignal(
            symbol=symbol,
            side=side,
            score=float(score),
            signal_price=float(signal_price),
            atr=float(atr),
            created_at=created_at,
            expires_at=created_at + timedelta(
                minutes=self.validity_minutes
            ),
        )

        self.signals[symbol] = signal
        return signal

    def get(
        self,
        symbol: str,
        now: Optional[datetime] = None,
    ) -> Optional[PendingSignal]:

        symbol = symbol.upper()
        signal = self.signals.get(symbol)

        if signal is None:
            return None

        if signal.is_expired(now) and signal.status == "PENDING":
            signal.expire()

        return signal

    def get_active(
        self,
        symbol: str,
        now: Optional[datetime] = None,
    ) -> Optional[PendingSignal]:

        signal = self.get(symbol, now)

        if signal is None or not signal.is_active(now):
            return None

        return signal

    def remove(self, symbol: str) -> Optional[PendingSignal]:
        return self.signals.pop(symbol.upper(), None)

    def reject(self, symbol: str, reason: str) -> Optional[PendingSignal]:
        signal = self.get(symbol)

        if signal is not None:
            signal.reject(reason)

        return signal

    def confirm(self, symbol: str) -> Optional[PendingSignal]:
        signal = self.get_active(symbol)

        if signal is not None:
            signal.confirm()

        return signal

    def execute(self, symbol: str) -> Optional[PendingSignal]:
        signal = self.get(symbol)

        if signal is not None:
            signal.execute()

        return signal

    def expire_signals(
        self,
        now: Optional[datetime] = None,
    ) -> list[PendingSignal]:

        now = now or datetime.now()
        expired = []

        for signal in self.signals.values():
            if (
                signal.status == "PENDING"
                and signal.is_expired(now)
            ):
                signal.expire()
                expired.append(signal)

        return expired

    def active_signals(
        self,
        now: Optional[datetime] = None,
    ) -> list[PendingSignal]:

        now = now or datetime.now()
        self.expire_signals(now)

        return [
            signal
            for signal in self.signals.values()
            if signal.is_active(now)
        ]

    def clear_inactive(self):
        inactive_symbols = [
            symbol
            for symbol, signal in self.signals.items()
            if signal.status != "PENDING"
        ]

        for symbol in inactive_symbols:
            del self.signals[symbol]

    def summary(self) -> dict:
        counts = {
            "PENDING": 0,
            "CONFIRMED": 0,
            "EXECUTED": 0,
            "REJECTED": 0,
            "EXPIRED": 0,
        }

        for signal in self.signals.values():
            counts[signal.status] = counts.get(signal.status, 0) + 1

        return {
            "total_signals": len(self.signals),
            "status_counts": counts,
            "active_signals": len(self.active_signals()),
        }