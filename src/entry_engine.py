from dataclasses import dataclass


@dataclass
class EntryDecision:

    approved: bool

    entry_price: float

    reason: str

    entry_score: float


class EntryEngine:

    def __init__(self):

        self.max_pullback_pct = 0.003
        self.max_breakout_pct = 0.008

    def evaluate(

        self,

        side: str,

        current_price: float,

        ema20: float,

        ema50: float,

        rsi14: float,

        macd: float,

        macd_signal: float,

    ) -> EntryDecision:

        side = side.upper()

        score = 0

        reasons = []

        if side == "BUY":

            distance = abs(current_price - ema20) / ema20

            if distance <= self.max_pullback_pct:

                score += 40
                reasons.append("Pullback to EMA20")

            elif current_price > ema20:

                score += 20
                reasons.append("Above EMA20")

            if macd > macd_signal:

                score += 30
                reasons.append("MACD Bullish")

            if 45 <= rsi14 <= 70:

                score += 30
                reasons.append("RSI Healthy")

        elif side == "SELL":

            distance = abs(current_price - ema20) / ema20

            if distance <= self.max_pullback_pct:

                score += 40
                reasons.append("Pullback to EMA20")

            elif current_price < ema20:

                score += 20
                reasons.append("Below EMA20")

            if macd < macd_signal:

                score += 30
                reasons.append("MACD Bearish")

            if 30 <= rsi14 <= 55:

                score += 30
                reasons.append("RSI Healthy")

        else:

            return EntryDecision(

                approved=False,

                entry_price=current_price,

                reason="Invalid side",

                entry_score=0,

            )

        approved = score >= 70

        return EntryDecision(

            approved=approved,

            entry_price=current_price,

            reason=" | ".join(reasons),

            entry_score=score,

        )