import pandas as pd
from pathlib import Path
from datetime import datetime

from config.symbols import SYMBOLS
from src.indicator_engine import IndicatorEngine
from src.signal_engine import SignalEngine


class AIBacktestReportEngine:

    def __init__(self):
        self.result_path = Path("logs/ai_backtest_report.csv")
        self.summary_path = Path("logs/ai_backtest_summary.txt")
        self.result_path.parent.mkdir(parents=True, exist_ok=True)

        self.balance = 5000
        self.risk_per_trade = 0.01
        self.take_profit_pct = 0.03
        self.stop_loss_pct = -0.015
        self.min_ai_score = 85
        self.timeframe = "15m"

    def run(self):
        results = []

        print("=" * 60)
        print("TCP AI BACKTEST LAB - PROFESSIONAL REPORT")
        print("=" * 60)

        for symbol in SYMBOLS:
            csv_path = f"data/{symbol}/15m/{symbol}_15m.csv"

            print("\n" + "=" * 60)
            print("Backtesting:", symbol)
            print("=" * 60)

            if not Path(csv_path).exists():
                print("CSV not found -> skipped")
                continue

            try:
                indicator = IndicatorEngine(csv_path)
                indicator.load_csv()
                indicator.calculate()
                indicator.save()

                signal = SignalEngine(csv_path)
                signal.load_csv()
                signal.generate()
                signal.save()

                df = pd.read_csv(csv_path)
                result = self.backtest(df)

                result["time"] = datetime.now().isoformat()
                result["symbol"] = symbol

                results.append(result)

                print("Period        :", result["start_date"], "to", result["end_date"])
                print("Total Days    :", result["total_days"])
                print("Total Bars    :", result["total_bars"])
                print("Trades        :", result["total_trades"])
                print("Win Rate      :", result["win_rate"])
                print("Net Profit    :", result["net_profit"])
                print("Profit Factor :", result["profit_factor"])
                print("Max Drawdown  :", result["max_drawdown"])

            except Exception as e:
                print(symbol, "ERROR :", e)

        if not results:
            print("No backtest results.")
            return

        report = pd.DataFrame(results)
        report = report.sort_values(
            by=["net_profit", "profit_factor", "win_rate"],
            ascending=False,
        )

        report.to_csv(self.result_path, index=False)

        best = report.iloc[0]
        worst = report.iloc[-1]

        total_trades = int(report["total_trades"].sum())
        total_wins = int(report["wins"].sum())
        total_losses = int(report["losses"].sum())
        total_net_profit = round(report["net_profit"].sum(), 2)

        overall_win_rate = (
            round(total_wins / total_trades * 100, 2)
            if total_trades > 0
            else 0
        )

        summary = f"""
============================================================
TCP AI BACKTEST LAB - PROFESSIONAL SUMMARY
============================================================

Backtest Version
- Timeframe        : {self.timeframe}
- Min AI Score     : {self.min_ai_score}
- Take Profit      : {self.take_profit_pct * 100}%
- Stop Loss        : {abs(self.stop_loss_pct) * 100}%
- Balance          : {self.balance}
- Risk Per Trade   : {self.risk_per_trade * 100}%

Portfolio Summary
- Symbols Tested   : {len(report)}
- Total Trades     : {total_trades}
- Wins             : {total_wins}
- Losses           : {total_losses}
- Overall Win Rate : {overall_win_rate}%
- Total Net Profit : {total_net_profit}

Ranking
- Best Symbol      : {best["symbol"]}
- Best Profit      : {best["net_profit"]}
- Worst Symbol     : {worst["symbol"]}
- Worst Profit     : {worst["net_profit"]}

Files
- CSV Report       : {self.result_path}
- Text Summary     : {self.summary_path}

============================================================
"""

        self.summary_path.write_text(summary, encoding="utf-8")

        print(summary)
        print(report.to_string(index=False))

    def backtest(self, df):
        df = df.copy()

        date_col = None
        for col in ["time", "timestamp", "datetime", "date", "open_time"]:
            if col in df.columns:
                date_col = col
                break

        if date_col:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            start_date = str(df[date_col].min())
            end_date = str(df[date_col].max())
            total_days = (
                df[date_col].max() - df[date_col].min()
            ).days if df[date_col].notna().any() else 0
        else:
            start_date = "N/A"
            end_date = "N/A"
            total_days = 0

        trades = []
        in_position = False
        entry_price = 0
        entry_index = 0
        entry_side = None

        for i in range(len(df)):
            row = df.iloc[i]

            price = float(row["close"])
            signal = str(row.get("Signal", "WAIT"))
            score = float(row.get("AI_SCORE", 0))

            if (
                not in_position
                and signal == "BUY"
                and score >= self.min_ai_score
            ):
                in_position = True
                entry_price = price
                entry_index = i
                entry_side = "BUY"

            elif in_position:
                profit_pct = (price - entry_price) / entry_price

                if (
                    profit_pct >= self.take_profit_pct
                    or profit_pct <= self.stop_loss_pct
                ):
                    profit = (
                        self.balance
                        * self.risk_per_trade
                        * (profit_pct / abs(self.stop_loss_pct))
                    )

                    trades.append({
                        "side": entry_side,
                        "profit": round(profit, 4),
                        "holding_bars": i - entry_index
                    })

                    in_position = False

        if not trades:
            return {
                "start_date": start_date,
                "end_date": end_date,
                "total_days": total_days,
                "total_bars": len(df),
                "timeframe": self.timeframe,
                "total_trades": 0,
                "buy_trades": 0,
                "sell_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "gross_profit": 0,
                "gross_loss": 0,
                "net_profit": 0,
                "profit_factor": 0,
                "max_drawdown": 0,
                "expectancy": 0,
                "average_win": 0,
                "average_loss": 0,
                "average_holding_bars": 0,
            }

        result = pd.DataFrame(trades)
        result["equity"] = result["profit"].cumsum()
        result["peak"] = result["equity"].cummax()
        result["drawdown"] = result["equity"] - result["peak"]

        wins = result[result["profit"] > 0]
        losses = result[result["profit"] < 0]

        gross_profit = wins["profit"].sum()
        gross_loss = losses["profit"].sum()
        net_profit = result["profit"].sum()

        total_trades = len(result)
        win_rate = len(wins) / total_trades * 100
        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else "Infinity"

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_days": total_days,
            "total_bars": len(df),
            "timeframe": self.timeframe,
            "total_trades": total_trades,
            "buy_trades": int((result["side"] == "BUY").sum()),
            "sell_trades": int((result["side"] == "SELL").sum()),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "net_profit": round(net_profit, 2),
            "profit_factor": profit_factor,
            "max_drawdown": round(result["drawdown"].min(), 2),
            "expectancy": round(result["profit"].mean(), 2),
            "average_win": round(wins["profit"].mean(), 2) if len(wins) > 0 else 0,
            "average_loss": round(losses["profit"].mean(), 2) if len(losses) > 0 else 0,
            "average_holding_bars": round(result["holding_bars"].mean(), 2),
        }


def main():
    engine = AIBacktestReportEngine()
    engine.run()


if __name__ == "__main__":
    main()