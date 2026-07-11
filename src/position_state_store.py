import json
from datetime import datetime
from pathlib import Path

from src.paper_position import PaperPosition


class PositionStateStore:

    def __init__(
        self,
        state_file: str = "logs/paper_state.json",
    ):
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        positions,
        risk_manager,
    ):
        state = {
            "version": 2,
            "saved_at": datetime.now().isoformat(),
            "positions": [
                position.to_dict()
                for position in positions
            ],
            "risk": {
                "state_date":
                    datetime.now().date().isoformat(),
                "daily_realized_pnl":
                    float(risk_manager.daily_realized_pnl),
                "consecutive_losses":
                    int(risk_manager.consecutive_losses),
                "cooldown_until": (
                    risk_manager.cooldown_until.isoformat()
                    if risk_manager.cooldown_until
                    else None
                ),
            },
        }

        temporary_file = self.state_file.with_suffix(
            ".json.tmp"
        )

        with open(
            temporary_file,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                state,
                file,
                indent=4,
                ensure_ascii=False,
            )

        temporary_file.replace(self.state_file)

    def load(self):
        if not self.state_file.exists():
            return {
                "positions": [],
                "risk": {},
            }

        try:
            with open(
                self.state_file,
                "r",
                encoding="utf-8",
            ) as file:
                state = json.load(file)

        except (
            json.JSONDecodeError,
            OSError,
        ):
            self._backup_corrupted_state()

            return {
                "positions": [],
                "risk": {},
            }

        positions = []

        for data in state.get("positions", []):
            position = self._restore_position(data)

            if position is not None:
                positions.append(position)

        return {
            "positions": positions,
            "risk": state.get("risk", {}),
        }

    def clear(self):
        if self.state_file.exists():
            self.state_file.unlink()

    def _restore_position(self, data):
        try:
            entry_price = float(data["entry_price"])
            quantity = float(data["quantity"])

            leverage = int(data.get("leverage", 1))

            notional_value = float(
                data.get(
                    "notional_value",
                    entry_price * quantity,
                )
            )

            required_margin = float(
                data.get(
                    "required_margin",
                    (
                        notional_value / leverage
                        if leverage > 0
                        else notional_value
                    ),
                )
            )

            return PaperPosition(
                symbol=str(data["symbol"]),
                side=str(data["side"]),
                entry_price=entry_price,
                quantity=quantity,
                entry_time=datetime.fromisoformat(
                    data["entry_time"]
                ),
                exit_price=(
                    float(data["exit_price"])
                    if data.get("exit_price") is not None
                    else None
                ),
                exit_time=(
                    datetime.fromisoformat(
                        data["exit_time"]
                    )
                    if data.get("exit_time")
                    else None
                ),
                status=str(
                    data.get("status", "OPEN")
                ),
                realized_pnl=float(
                    data.get("realized_pnl", 0.0)
                ),
                unrealized_pnl=float(
                    data.get("unrealized_pnl", 0.0)
                ),
                stop_loss=(
                    float(data["stop_loss"])
                    if data.get("stop_loss") is not None
                    else None
                ),
                take_profit=(
                    float(data["take_profit"])
                    if data.get("take_profit") is not None
                    else None
                ),
                trailing_stop=(
                    float(data["trailing_stop"])
                    if data.get("trailing_stop") is not None
                    else None
                ),
                strategy_score=float(
                    data.get("strategy_score", 0.0)
                ),
                signal=str(
                    data.get("signal", "")
                ),
                exit_reason=str(
                    data.get("exit_reason", "")
                ),
                leverage=leverage,
                margin_mode=str(
                    data.get(
                        "margin_mode",
                        "ISOLATED",
                    )
                ),
                notional_value=notional_value,
                required_margin=required_margin,
                risk_amount=float(
                    data.get("risk_amount", 0.0)
                ),
                entry_fee=float(
                    data.get("entry_fee", 0.0)
                ),
                exit_fee=float(
                    data.get("exit_fee", 0.0)
                ),
                funding_fee=float(
                    data.get("funding_fee", 0.0)
                ),
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            return None

    def _backup_corrupted_state(self):
        if not self.state_file.exists():
            return

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        backup_file = self.state_file.with_name(
            f"{self.state_file.stem}"
            f"_corrupted_{timestamp}.json"
        )

        try:
            self.state_file.replace(backup_file)
        except OSError:
            pass