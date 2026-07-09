import json
import pandas as pd
from pathlib import Path


class FinalBacktestAnalysis:

    def __init__(self):
        self.strategy_path = Path("research/best_strategy.json")
        self.output_path = Path("research/final_trade_analysis.csv")
        self.summary_path = Path("research/final_trade_analysis_summary.txt")
        self.timeframe = "15m"
        self.balance = 5000
        self.risk_per_trade = 0.01

    def run(self):
        if not self.strategy_path.exists():
            print("best_strategy.json not found")
            return

        strategy = json.loads(self.strategy_path.read_text(encoding="utf-8"))
        symbol = strategy["symbol"]

        csv_path = Path(f"data/{symbol}/{self.timeframe}/{symbol}_{self.timeframe}.csv")

        if not csv_path.exists():
            print("CSV not found:", csv_path)
            return

        df = pd.read_csv(csv_path)
        df = df.dropna().reset_index(drop=True)

        df["ATR_MA50"] = df["ATR14"].rolling(50).mean()
        df["VOLUME_MA50"] = df["volume"].rolling(50).mean()
        df = df.dropna().reset_index(drop=True)

        trades = self.backtest(df, strategy)

        if not trades:
            print("No trades found")
            return

        report = pd.DataFrame(trades)
        report.to_csv(self.output_path, index=False)

        summary = self.create_summary(report, strategy)
        self.summary_path.write_text(summary, encoding="utf-8")

        print(summary)
        print("Saved ->", self.output_path)
        print("Saved ->", self.summary_path)

    def backtest(self, df, strategy):
        trades = []
        in_position = False
        entry_price = 0
        entry_index = 0
        entry_row = None

        min_score = int(strategy["min_score"])
        tp = float(strategy["take_profit_pct"])
        sl = float(strategy["stop_loss_pct"])
        rsi_range = strategy["rsi_range"]

        if rsi_range != "None":
            rsi_range = rsi_range.replace("(", "").replace(")", "")
            rsi_low, rsi_high = [float(x.strip()) for x in rsi_range.split(",")]
        else:
            rsi_low, rsi_high = None, None

        for i in range(len(df)):
            row = df.iloc[i]
            price = float(row["close"])
            signal = str(row.get("Signal", "WAIT"))
            score = float(row.get("AI_SCORE", 0))

            if not in_position:
                if signal != "BUY":
                    continue

                if score < min_score:
                    continue

                if rsi_low is not None:
                    rsi = float(row["RSI14"])
                    if not (rsi_low <= rsi <= rsi_high):
                        continue

                if not (
                    row["EMA20"] > row["EMA50"]
                    and row["EMA50"] > row["EMA200"]
                ):
                    continue

                if bool(strategy.get("atr_filter", False)):
                    if row["ATR14"] <= row["ATR_MA50"]:
                        continue

                if bool(strategy.get("volume_filter", False)):
                    if row["volume"] <= row["VOLUME_MA50"]:
                        continue

                in_position = True
                entry_price = price
                entry_index = i
                entry_row = row
                continue

            profit_pct = (price - entry_price) / entry_price

            if profit_pct >= tp or profit_pct <= sl:
                profit = (
                    self.balance
                    * self.risk_per_trade
                    * (profit_pct / abs(sl))
                )

                reason = self.classify_loss(entry_row, row, profit)

                trades.append({
                    "entry_index": entry_index,
                    "exit_index": i,
                    "holding_bars": i - entry_index,
                    "entry_price": round(entry_price, 6),
                    "exit_price": round(price, 6),
                    "profit": round(profit, 4),
                    "profit_pct": round(profit_pct * 100, 4),
                    "result": "WIN" if profit > 0 else "LOSS",
                    "ai_score": float(entry_row.get("AI_SCORE", 0)),
                    "rsi": float(entry_row.get("RSI14", 0)),
                    "atr_pct": round(float(entry_row.get("ATR14", 0)) / entry_price * 100, 4),
                    "volume_ratio": round(
                        float(entry_row.get("volume", 0)) /
                        float(entry_row.get("VOLUME_MA50", 1)),
                        4
                    ),
                    "ema_gap_pct": round(
                        (float(entry_row.get("EMA20", 0)) -
                         float(entry_row.get("EMA50", 0))) /
                        entry_price * 100,
                        4
                    ),
                    "loss_reason": reason,
                })

                in_position = False

        return trades

    def classify_loss(self, entry, exit_row, profit):
        if profit > 0:
            return "WIN"

        rsi = float(entry.get("RSI14", 0))
        volume = float(entry.get("volume", 0))
        volume_ma = float(entry.get("VOLUME_MA50", 1))
        atr = float(entry.get("ATR14", 0))
        atr_ma = float(entry.get("ATR_MA50", 1))
        ema20 = float(entry.get("EMA20", 0))
        ema50 = float(entry.get("EMA50", 0))

        if volume < volume_ma:
            return "LOW_VOLUME"

        if atr < atr_ma:
            return "LOW_VOLATILITY"

        if rsi > 70:
            return "RSI_TOO_HIGH"

        if ema20 <= ema50:
            return "WEAK_TREND"

        return "FALSE_SIGNAL"

    def create_summary(self, report, strategy):
        wins = report[report["result"] == "WIN"]
        losses = report[report["result"] == "LOSS"]

        gross_profit = wins["profit"].sum()
        gross_loss = losses["profit"].sum()
        net_profit = report["profit"].sum()
        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else "Infinity"

        loss_reasons = losses["loss_reason"].value_counts().to_string()

        summary = f"""
============================================================
TCP FINAL TRADE ANALYSIS
============================================================

Strategy
{json.dumps(strategy, indent=4)}

Performance
Total Trades     : {len(report)}
Wins             : {len(wins)}
Losses           : {len(losses)}
Win Rate         : {round(len(wins) / len(report) * 100, 2)}%
Gross Profit     : {round(gross_profit, 2)}
Gross Loss       : {round(gross_loss, 2)}
Net Profit       : {round(net_profit, 2)}
Profit Factor    : {profit_factor if profit_factor == "Infinity" else round(profit_factor, 4)}
Average Win      : {round(wins["profit"].mean(), 2) if len(wins) else 0}
Average Loss     : {round(losses["profit"].mean(), 2) if len(losses) else 0}
Avg Holding Bars : {round(report["holding_bars"].mean(), 2)}

Loss Analysis
{loss_reasons}

Recommendation
- If LOW_VOLUME is high: keep or strengthen volume filter.
- If FALSE_SIGNAL is high: add confirmation before entry.
- If RSI_TOO_HIGH is high: reduce RSI upper range.
- If LOW_VOLATILITY is high: keep ATR filter.

Files
Trade Analysis : {self.output_path}
Summary        : {self.summary_path}

============================================================
"""
        return summary


def main():
    FinalBacktestAnalysis().run()


if __name__ == "__main__":
    main()