import json
import pandas as pd
from pathlib import Path
from line_alert import LineAlert


class AlertEngine:

    def __init__(self, csv_path, state_path="logs/alert_state.json"):
        self.csv_path = csv_path
        self.state_path = Path(state_path)

    def load_state(self):
        if self.state_path.exists():
            with open(self.state_path, "r") as file:
                return json.load(file)

        return {
            "last_decision": "",
            "last_score": 0
        }

    def save_state(self, state):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.state_path, "w") as file:
            json.dump(state, file, indent=4)

    def should_alert(self, decision, score, last_state):
        last_decision = last_state.get("last_decision", "")
        last_score = last_state.get("last_score", 0)

        if decision in ["BUY", "SELL"] and decision != last_decision:
            return True

        if abs(float(score) - float(last_score)) >= 20:
            return True

        return False

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

        state = self.load_state()

        if not self.should_alert(decision, score, state):
            print("No important change. Alert skipped.")
            return

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

        self.save_state({
            "last_decision": str(decision),
            "last_score": float(score)
        })


def main():
    engine = AlertEngine(
        "data/BTCUSDT/15m/BTCUSDT_15m.csv"
    )
    engine.run()


if __name__ == "__main__":
    main()