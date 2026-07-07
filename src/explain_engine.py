import pandas as pd


class ExplainEngine:

    def __init__(self, csv_path="data/BTCUSDT/15m/BTCUSDT_15m.csv"):
        self.csv_path = csv_path

    def explain_latest(self):
        df = pd.read_csv(self.csv_path)
        latest = df.iloc[-1]

        price = latest.get("close", 0)
        score = latest.get("AI_SCORE", 0)
        signal = latest.get("Signal", "WAIT")

        reasons = []

        if latest.get("EMA20", 0) > latest.get("EMA50", 0):
            reasons.append("EMA Trend: Bullish")
        else:
            reasons.append("EMA Trend: Bearish")

        rsi = latest.get("RSI14", 0)
        if 45 <= rsi <= 65:
            reasons.append(f"RSI Healthy: {round(rsi, 2)}")
        elif rsi > 70:
            reasons.append(f"RSI Overbought: {round(rsi, 2)}")
        else:
            reasons.append(f"RSI Weak: {round(rsi, 2)}")

        if "MACD" in latest and latest.get("MACD", 0) > 0:
            reasons.append("MACD: Bullish")
        else:
            reasons.append("MACD: Weak")

        confidence = "HIGH" if score >= 80 else "MEDIUM" if score >= 60 else "LOW"

        message = f"""
==============================
AI Explain Report
==============================
Symbol     : BTCUSDT
Price      : {price}
Signal     : {signal}
AI Score   : {round(score, 2)}
Confidence : {confidence}

Reasons:
- {reasons[0]}
- {reasons[1]}
- {reasons[2]}
==============================
"""

        print(message)
        return message


def main():
    engine = ExplainEngine()
    engine.explain_latest()


if __name__ == "__main__":
    main()