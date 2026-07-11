from dataclasses import dataclass


@dataclass
class ConfirmationResult:
    approved: bool
    score: float
    reason: str


class ConfirmationEngine:

    def confirm(
        self,
        side: str,
        ema20: float,
        ema50: float,
        macd: float,
        macd_signal: float,
        rsi14: float,
        volume: float,
        volume_ma20: float,
    ) -> ConfirmationResult:

        side = side.upper()
        score = 0.0
        reasons = []

        if side == "BUY":
            if ema20 > ema50:
                score += 35
                reasons.append("5m trend bullish")

            if macd > macd_signal:
                score += 25
                reasons.append("5m MACD bullish")

            if 45 <= rsi14 <= 72:
                score += 20
                reasons.append("5m RSI valid")

            if volume > volume_ma20:
                score += 20
                reasons.append("5m volume confirmed")

        elif side == "SELL":
            if ema20 < ema50:
                score += 35
                reasons.append("5m trend bearish")

            if macd < macd_signal:
                score += 25
                reasons.append("5m MACD bearish")

            if 28 <= rsi14 <= 55:
                score += 20
                reasons.append("5m RSI valid")

            if volume > volume_ma20:
                score += 20
                reasons.append("5m volume confirmed")

        else:
            return ConfirmationResult(
                approved=False,
                score=0.0,
                reason="Invalid side",
            )

        approved = score >= 60

        return ConfirmationResult(
            approved=approved,
            score=score,
            reason="; ".join(reasons) if reasons else "No confirmation",
        )