import pandas as pd
from pathlib import Path
from datetime import datetime


class TradeLogger:

    def __init__(self, csv_path, log_path="logs/trade_log.csv"):
        self.csv_path = csv_path
        self.log_path = Path(log_path)
        self.df = None

    def load_csv(self):
        print("Loading CSV...")
        self.df = pd.read_csv(self.csv_path)

    def create_log(self):
        print("Creating trade log...")

        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        latest = self.df.iloc[-1]

        log_data = {
            "log_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "close": latest["close"],
            "AI_SCORE": latest.get("AI_SCORE", ""),
            "AI_DECISION": latest.get("AI_DECISION", ""),
            "AI_SIGNAL": latest.get("AI_SIGNAL", ""),
            "StrategyScore": latest.get("StrategyScore", ""),
            "Confidence": latest.get("Confidence", ""),
            "Reason": latest.get("Reason", "")
        }

        log_df = pd.DataFrame([log_data])

        if self.log_path.exists():
            log_df.to_csv(self.log_path, mode="a", header=False, index=False)
        else:
            log_df.to_csv(self.log_path, index=False)

        print("Saved ->", self.log_path)

    def run(self):
        self.load_csv()
        self.create_log()


def main():
    logger = TradeLogger(
        "data/BTCUSDT/15m/BTCUSDT_15m.csv"
    )
    logger.run()


if __name__ == "__main__":
    main()