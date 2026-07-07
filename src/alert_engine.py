import pandas as pd
from line_alert import LineAlert


class AlertEngine:

    def __init__(self, csv_path):
        self.csv_path = csv_path

    def run(self):
        df = pd.read_csv(self.csv_path)
        latest = df.iloc[-1]

        symbol = "BTCUSDT"
        close = latest.get("close", 0)
        decision = latest.get("AI_DECISION", "WAIT")
        score = latest.get("AI_SCORE", 0)
        signal = latest.get("Signal", "-")
        strategy_score = latest.get("StrategyScore", "-")
        reason = latest.get("Reason", "-")

        message = f"""
🤖 TCP Crypto AI Trader

Symbol: {symbol}
Timeframe: 15m

Decision: {decision}
AI Score: {score}
Signal: {signal}
Strategy Score: {strategy_score}

Price: {close}

Reason:
{reason}
"""

        line = LineAlert()
        line.send(message)


def main():
    engine = AlertEngine(
        "data/BTCUSDT/15m/BTCUSDT_15m.csv"
    )
    engine.run()


if __name__ == "__main__":
    main()