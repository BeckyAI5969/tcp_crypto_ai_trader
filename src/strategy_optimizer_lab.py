import pandas as pd
from pathlib import Path
from datetime import datetime
from itertools import product

from config.symbols import SYMBOLS
from src.indicator_engine import IndicatorEngine
from src.signal_engine import SignalEngine


class StrategyOptimizerLab:

    def __init__(self):
        self.result_path = Path("logs/strategy_optimizer_lab.csv")
        self.result_path.parent.mkdir(parents=True, exist_ok=True)

        self.balance = 5000
        self.risk_per_trade = 0.01

        self.score_list = [60, 65, 70, 75, 80, 85, 90]
        self.tp_sl_list = [
            (0.02, -0.01),
            (0.03, -0.015),
            (0.04, -0.02),
        ]
        self.trend_filter_list = [False, True]
        self.rsi_filter_list = [False, True]

    def run(self):
        results = []

        total_case = (
            len(SYMBOLS)
            * len(self.score_list)
            * len(self.tp_sl_list)
            * len(self.trend_filter_list)
            * len(self.rsi_filter_list)
        )

        current = 0

        print("=" * 70)
        print("TCP STRATEGY OPTIMIZER LAB")
        print("=" * 70)

        for symbol in SYMBOLS:
            csv_path = f"data/{symbol}/15m/{symbol}_15m.csv"

            if not Path(csv_path).exists():
                print(symbol, "CSV not found -> skipped")
                continue

            print("Preparing:", symbol)

            indicator = IndicatorEngine(csv_path)
            indicator.load_csv()
            indicator.calculate()
            indicator.save()

            signal = SignalEngine(csv_path)
            signal.load_csv()
            signal.generate()
            signal.save()

            df = pd.read_csv(csv_path)

            for score, tp_sl, trend_filter, rsi_filter in product(
                self.score_list,
                self.tp_sl_list,
                self.trend_filter_list,
                self.rsi_filter_list,
            ):
                tp, sl = tp_sl
                current += 1

                print(
                    f"[{current}/{total_case}] {symbol} | "
                    f"Score={score} | TP={tp} | SL={sl} | "
                    f"Trend={trend_filter} | RSI={rsi_filter}"
                )

                result = self.backtest(
                    df=df,
                    min_score=score,
                    take_profit_pct=tp,
                    stop_loss_pct=sl,
                    trend_filter=trend_filter,
                    rsi_filter=rsi_filter,
                )

                result.update({
                    "time": datetime.now().isoformat(),
                    "symbol": symbol,
                    "min_score": score,
                    "take_profit_pct": tp,
                    "stop_loss_pct": sl,
                    "trend_filter": trend_filter,
                    "rsi_filter": rsi_filter,
                })

                results.append(result)

        if not results:
            print("No optimizer results.")
            return

        report = pd.DataFrame(results)

        full_report = report.copy()

        report = report[report["trades"] >= 30]

        if report.empty:
            print("No strategy found with trades >= 30.")
            print("Saving full unfiltered report instead.")
            report = full_report

        report = report.sort_values(
            by=["profit_factor_score", "net_profit", "win_rate"],
            ascending=False,
        )

        report.to_csv(self.result_path, index=False)

        print("=" * 70)
        print("BEST 20 RESULTS")
        print("=" * 70)
        print(report.head(20).to_string(index=False))
        print("=" * 70)
        print("Saved ->", self.result_path)

    def backtest(
        self,
        df,
        min_score,
        take_profit_pct,
        stop_loss_pct,
        trend_filter,
        rsi_filter,
    ):
        trades = []
        in_position = False
        entry_price = 0

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

                if trend_filter:
                    if row["EMA50"] <= row["EMA200"]:
                        continue

                if rsi_filter:
                    rsi = float(row["RSI14"])
                    if not (35 <= rsi <= 65):
                        continue

                in_position = True
                entry_price = price
                continue

            profit_pct = (price - entry_price) / entry_price

            if (
                profit_pct >= take_profit_pct
                or profit_pct <= stop_loss_pct
            ):
                profit = (
                    self.balance
                    * self.risk_per_trade
                    * (profit_pct / abs(stop_loss_pct))
                )

                trades.append(round(profit, 4))
                in_position = False

        if not trades:
            return {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "gross_profit": 0,
                "gross_loss": 0,
                "net_profit": 0,
                "profit_factor": 0,
                "profit_factor_score": 0,
                "max_drawdown": 0,
                "expectancy": 0,
            }

        result = pd.DataFrame({"profit": trades})
        result["equity"] = result["profit"].cumsum()
        result["peak"] = result["equity"].cummax()
        result["drawdown"] = result["equity"] - result["peak"]

        wins = result[result["profit"] > 0]
        losses = result[result["profit"] < 0]

        gross_profit = wins["profit"].sum()
        gross_loss = losses["profit"].sum()
        net_profit = result["profit"].sum()

        win_rate = len(wins) / len(result) * 100
        profit_factor = (
            abs(gross_profit / gross_loss)
            if gross_loss != 0
            else float("inf")
        )

        return {
            "trades": len(result),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "net_profit": round(net_profit, 2),
            "profit_factor": round(profit_factor, 4)
            if profit_factor != float("inf")
            else "Infinity",
            "profit_factor_score": profit_factor
            if profit_factor != float("inf")
            else 999999,
            "max_drawdown": round(result["drawdown"].min(), 2),
            "expectancy": round(result["profit"].mean(), 2),
        }


def main():
    StrategyOptimizerLab().run()


if __name__ == "__main__":
    main()