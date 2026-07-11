from dataclasses import dataclass

from src.risk_config import DEFAULT_RISK_CONFIG


@dataclass
class ATRStopResult:

    stop_loss: float

    take_profit: float

    atr: float

    atr_multiplier: float

    risk_reward_ratio: float


class ATRStop:

    def __init__(self, config=DEFAULT_RISK_CONFIG):

        self.config = config

    def calculate(

        self,

        side: str,

        entry_price: float,

        atr: float,

    ) -> ATRStopResult:

        atr_distance = atr * self.config.atr_multiplier

        if side == "BUY":

            stop_loss = entry_price - atr_distance

            take_profit = (
                entry_price
                + atr_distance
                * self.config.risk_reward_ratio
            )

        else:

            stop_loss = entry_price + atr_distance

            take_profit = (
                entry_price
                - atr_distance
                * self.config.risk_reward_ratio
            )

        return ATRStopResult(

            stop_loss=round(stop_loss, 8),

            take_profit=round(take_profit, 8),

            atr=round(atr, 8),

            atr_multiplier=self.config.atr_multiplier,

            risk_reward_ratio=self.config.risk_reward_ratio,

        )