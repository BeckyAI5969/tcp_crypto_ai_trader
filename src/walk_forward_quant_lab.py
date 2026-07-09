import json
from pathlib import Path
from datetime import datetime
from itertools import product

import pandas as pd

from config.symbols import SYMBOLS
from src.indicator_engine import IndicatorEngine
from src.signal_engine import SignalEngine


class WalkForwardQuantLab:

    def __init__(self):
        self.timeframe = "15m"
        self.report_path = Path("research/walk_forward_report.csv")
        self.summary_path = Path("research/walk_forward_summary.txt")
        self.strategy_path = Path("research/best_strategy_verified.json")

        self.report_path.parent.mkdir(parents=True, exist_ok=True)

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

        self.min_test_trades = 20

    def run(self):
        rows = []

        print("=" * 70)
        print("TCP WALK-FORWARD QUANT LAB")
        print("=" * 70)

        for symbol in SYMBOLS:
            csv_path = Path(f"data/{symbol}/{self.timeframe}/{symbol}_{self.timeframe}.csv")

            if not csv_path.exists():
                print(symbol, "CSV not found -> skipped")
                continue

            print("Preparing:", symbol)

            indicator = IndicatorEngine(str(csv_path))
            indicator.load_csv()
            indicator.calculate()
            indicator.save()

            signal = SignalEngine(str(csv_path))
            signal.load_csv()
            signal.generate()
            signal.save()

            df = pd.read_csv(csv_path)
            df = df.dropna().reset_index(drop=True)

            if len(df) < 1000:
                print(symbol, "not enough data -> skipped")
                continue

            split_index = int(len(df) * 0.7)

            train_df = df.iloc[:split_index].copy()
            test_df = df.iloc[split_index:].copy()

            print(symbol, "Train Bars:", len(train_df), "Test Bars:", len(test_df))

            train_results = []

            for score, tp_sl, trend_filter, rsi_filter in product(
                self.score_list,
                self.tp_sl_list,
                self.trend_filter_list,
                self.rsi_filter_list,
            ):
                tp, sl = tp_sl

                result = self.backtest(
                    df=train_df,
                    min_score=score,
                    take_profit_pct=tp,
                    stop_loss_pct=sl,
                    trend_filter=trend_filter,
                    rsi_filter=rsi_filter,
                )

                result.update({
                    "symbol": symbol,
                    "phase": "TRAIN",
                    "min_score": score,
                    "take_profit_pct": tp,
                    "stop_loss_pct": sl,
                    "trend_filter": trend_filter,
                    "rsi_filter": rsi_filter,
                })

                train_results.append(result)

            train_report = pd.DataFrame(train_results)
            train_report = train_report[train_report["trades"] >= 30]

            if train_report.empty:
                print(symbol, "no valid train strategy")
                continue

            train_report = train_report.sort_values(
                by=["profit_factor_score", "net_profit", "win_rate"],
                ascending=False,
            )

            best_train = train_report.iloc[0]

            test_result = self.backtest(
                df=test_df,
                min_score=int(best_train["min_score"]),
                take_profit_pct=float(best_train["take_profit_pct"]),
                stop_loss_pct=float(best_train["stop_loss_pct"]),
                trend_filter=bool(best_train["trend_filter"]),
                rsi_filter=bool(best_train["rsi_filter"]),
            )

            test_result.update({
                "symbol": symbol,
                "phase": "TEST",
                "min_score": int(best_train["min_score"]),
                "take_profit_pct": float(best_train["take_profit_pct"]),
                "stop_loss_pct": float(best_train["stop_loss_pct"]),
                "trend_filter": bool(best_train["trend_filter"]),
                "rsi_filter": bool(best_train["rsi_filter"]),
                "train_profit_factor": best_train["profit_factor"],
                "train_net_profit": best_train["net_profit"],
                "train_win_rate": best_train["win_rate"],
                "time": datetime.now().isoformat(),
            })

            rows.append(test_result)

            print(
                symbol,
                "TEST PF:",
                test_result["profit_factor"],
                "NET:",
                test_result["net_profit"],
                "TRADES:",
                test_result["trades"],
            )

        if not rows:
            print("No walk-forward results.")
            return

        report = pd.DataFrame(rows)

        report["passed"] = (
            (report["trades"] >= self.min_test_trades)
            & (report["profit_factor_score"] > 1.0)
            & (report["net_profit"] > 0)
        )

        report = report.sort_values(
            by=["passed", "profit_factor_score", "net_profit"],
            ascending=False,
        )

        report.to_csv(self.report_path, index=False)

        best = report.iloc[0]

        strategy = {
            "created_at": datetime.now().isoformat(),
            "strategy_name": "TCP_WALK_FORWARD_VERIFIED_V1",
            "symbol": best["symbol"],
            "timeframe": self.timeframe,
            "min_score": int(best["min_score"]),
            "take_profit_pct": float(best["take_profit_pct"]),
            "stop_loss_pct": float(best["stop_loss_pct"]),
            "trend_filter": bool(best["trend_filter"]),
            "rsi_filter": bool(best["rsi_filter"]),
            "test_trades": int(best["trades"]),
            "test_win_rate": float(best["win_rate"]),
            "test_net_profit": float(best["net_profit"]),
            "test_profit_factor": best["profit_factor"],
            "test_max_drawdown": float(best["max_drawdown"]),
            "passed": bool(best["passed"]),
        }

        self.strategy_path.write_text(
            json.dumps(strategy, indent=4),
            encoding="utf-8",
        )

        summary = f"""
======================================================================
TCP WALK-FORWARD QUANT LAB SUMMARY
======================================================================

Generated At : {datetime.now()}

Report       : {self.report_path}
Strategy     : {self.strategy_path}

Best Strategy
{json.dumps(strategy, indent=4)}

Top Results
{report.head(20).to_string(index=False)}

======================================================================
"""

        self.summary_path.write_text(summary, encoding="utf-8")

        print(summary)

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

                if trend_filter and row["EMA50"] <= row["EMA200"]:
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
    WalkForwardQuantLab().run()


if __name__ == "__main__":
    main()