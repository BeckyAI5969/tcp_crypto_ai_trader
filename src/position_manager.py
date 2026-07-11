from dataclasses import dataclass
from datetime import datetime, timedelta

from src.paper_position import PaperPosition


@dataclass
class PositionUpdateResult:
    position: PaperPosition | None
    closed: bool
    reason: str
    action: str


class PositionManager:

    def __init__(
        self,
        break_even_trigger_r: float = 1.0,
        trailing_trigger_r: float = 1.5,
        trailing_distance_r: float = 1.0,
        max_holding_minutes: int = 720,
    ):
        self.break_even_trigger_r = break_even_trigger_r
        self.trailing_trigger_r = trailing_trigger_r
        self.trailing_distance_r = trailing_distance_r
        self.max_holding_minutes = max_holding_minutes

        self.closed_position_keys = set()

    def update_position(
        self,
        position: PaperPosition,
        price: float,
        now: datetime | None = None,
    ) -> PositionUpdateResult:

        if position is None:
            return PositionUpdateResult(
                position=None,
                closed=False,
                reason="POSITION_NOT_FOUND",
                action="NONE",
            )

        if not position.is_open():
            return PositionUpdateResult(
                position=position,
                closed=False,
                reason="POSITION_ALREADY_CLOSED",
                action="NONE",
            )

        now = now or datetime.now()

        position.update_price(price)

        time_exit = self._check_time_exit(position, now)

        if time_exit:
            return self._close_once(
                position=position,
                price=price,
                reason="TIME_EXIT",
            )

        should_close, close_reason = position.should_close(price)

        if should_close:
            return self._close_once(
                position=position,
                price=price,
                reason=close_reason,
            )

        self._apply_break_even(position, price)
        self._apply_trailing_stop(position, price)

        should_close, close_reason = position.should_close(price)

        if should_close:
            return self._close_once(
                position=position,
                price=price,
                reason=close_reason,
            )

        return PositionUpdateResult(
            position=position,
            closed=False,
            reason="POSITION_UPDATED",
            action="UPDATE",
        )

    def close_position(
        self,
        position: PaperPosition,
        price: float,
        reason: str = "MANUAL",
    ) -> PositionUpdateResult:

        if position is None:
            return PositionUpdateResult(
                position=None,
                closed=False,
                reason="POSITION_NOT_FOUND",
                action="NONE",
            )

        if not position.is_open():
            return PositionUpdateResult(
                position=position,
                closed=False,
                reason="POSITION_ALREADY_CLOSED",
                action="NONE",
            )

        return self._close_once(
            position=position,
            price=price,
            reason=reason,
        )

    def _apply_break_even(
        self,
        position: PaperPosition,
        price: float,
    ):

        initial_risk = self._initial_risk_distance(position)

        if initial_risk <= 0:
            return

        trigger_distance = initial_risk * self.break_even_trigger_r

        if position.side == "BUY":
            if price >= position.entry_price + trigger_distance:
                if (
                    position.stop_loss is None
                    or position.stop_loss < position.entry_price
                ):
                    position.stop_loss = position.entry_price

        else:
            if price <= position.entry_price - trigger_distance:
                if (
                    position.stop_loss is None
                    or position.stop_loss > position.entry_price
                ):
                    position.stop_loss = position.entry_price

    def _apply_trailing_stop(
        self,
        position: PaperPosition,
        price: float,
    ):

        initial_risk = self._initial_risk_distance(position)

        if initial_risk <= 0:
            return

        trigger_distance = initial_risk * self.trailing_trigger_r
        trailing_distance = initial_risk * self.trailing_distance_r

        if position.side == "BUY":
            if price < position.entry_price + trigger_distance:
                return

            new_stop = price - trailing_distance

            if (
                position.trailing_stop is None
                or new_stop > position.trailing_stop
            ):
                position.trailing_stop = new_stop

            if (
                position.stop_loss is None
                or position.trailing_stop > position.stop_loss
            ):
                position.stop_loss = position.trailing_stop

        else:
            if price > position.entry_price - trigger_distance:
                return

            new_stop = price + trailing_distance

            if (
                position.trailing_stop is None
                or new_stop < position.trailing_stop
            ):
                position.trailing_stop = new_stop

            if (
                position.stop_loss is None
                or position.trailing_stop < position.stop_loss
            ):
                position.stop_loss = position.trailing_stop

    def _check_time_exit(
        self,
        position: PaperPosition,
        now: datetime,
    ) -> bool:

        if self.max_holding_minutes <= 0:
            return False

        maximum_holding = timedelta(
            minutes=self.max_holding_minutes
        )

        return now - position.entry_time >= maximum_holding

    def _initial_risk_distance(
        self,
        position: PaperPosition,
    ) -> float:

        if position.stop_loss is None:
            return 0.0

        return abs(
            position.entry_price - position.stop_loss
        )

    def _close_once(
        self,
        position: PaperPosition,
        price: float,
        reason: str,
    ) -> PositionUpdateResult:

        position_key = self._position_key(position)

        if position_key in self.closed_position_keys:
            return PositionUpdateResult(
                position=position,
                closed=False,
                reason="DUPLICATE_CLOSE_BLOCKED",
                action="NONE",
            )

        position.close(
            exit_price=price,
            reason=reason,
        )

        self.closed_position_keys.add(position_key)

        return PositionUpdateResult(
            position=position,
            closed=True,
            reason=reason,
            action="CLOSE",
        )

    def _position_key(
        self,
        position: PaperPosition,
    ) -> str:

        return (
            f"{position.symbol}|"
            f"{position.side}|"
            f"{position.entry_time.isoformat()}|"
            f"{position.entry_price}|"
            f"{position.quantity}"
        )