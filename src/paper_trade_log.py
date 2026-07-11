import json
from pathlib import Path
from datetime import datetime

import pandas as pd


class PaperTradeLogger:

    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        self.trade_csv = self.log_dir / "paper_trade_log.csv"
        self.trade_jsonl = self.log_dir / "paper_trade_log.jsonl"

    def log_open(self, position):
        record = position.to_dict()
        record["event"] = "OPEN"
        record["logged_at"] = datetime.now().isoformat()
        self._save(record)

    def log_update(self, position):
        record = position.to_dict()
        record["event"] = "UPDATE"
        record["logged_at"] = datetime.now().isoformat()
        self._save(record)

    def log_close(self, position):
        record = position.to_dict()
        record["event"] = "CLOSE"
        record["logged_at"] = datetime.now().isoformat()
        self._save(record)

    def _save(self, record):
        df = pd.DataFrame([record])

        if self.trade_csv.exists():
            df.to_csv(self.trade_csv, mode="a", header=False, index=False)
        else:
            df.to_csv(self.trade_csv, index=False)

        with open(self.trade_jsonl, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def load(self):
        if not self.trade_csv.exists():
            return pd.DataFrame()

        try:
            return pd.read_csv(self.trade_csv)
        except pd.errors.ParserError:
            self.trade_csv.unlink()
            return pd.DataFrame()

    def total_trades(self):
        df = self.load()

        if df.empty or "event" not in df.columns:
            return 0

        return len(df[df["event"] == "CLOSE"])

    def clear(self):
        if self.trade_csv.exists():
            self.trade_csv.unlink()

        if self.trade_jsonl.exists():
            self.trade_jsonl.unlink()