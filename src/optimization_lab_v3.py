import json
from pathlib import Path
from datetime import datetime
from itertools import product

import pandas as pd

from config.symbols import SYMBOLS


class OptimizationLabV3:

    def __init__(self):
        self.timeframe = "15m"

        self.result_path = Path("research/optimization_lab_v3_fast.csv")
        self.best_path = Path("research/optimization_lab_v3_best.csv")
        self.strategy_path = Path("research/best_strategy_v3.json")

        self.result_path.parent.mkdir(parents=True, exist_ok=True)

        self.balance = 5000
        self.risk_per_trade = 0.01

        self.score_list = [80, 85]
        self.tp_sl_list = [
            (0.05, -0.015),
            (0.06, -0.015),
            (0.06, -0.02),
        ]

        self.rsi_ranges = [
            (35, 70),
            (40, 70),
        ]

        self.ema_filters = [
            "ema20_gt_ema50_and_ema50_gt_ema200",
        ]

        self.atr_filter_list = [True]
        self.volume_filter_list = [False, True]
        self.breakout_filter_list = [False, True]

    def run(self):
        results = []

        print("=" * 70)
        print("TCP OPTIMIZATION LAB V3 FAST")
        print("=" * 70)

        total = (
            len(SYMBOLS)
            * len(self.score_list)
            * len(self.tp_sl_list)
            * len(self.rsi_ranges)
            * len(self.ema_filters)
            * len(self.atr_filter_list)
            * len(self.volume_filter_list)
            * len(self.breakout_filter_list)
        )

        current = 0

        for symbol in SYMBOLS:
            csv_path = Path(
                f"data/{symbol}/{self.timeframe}/{symbol}_{self.timeframe}.csv"
            )

            if not csv_path.exists():
                print(symbol, "CSV not found -> skipped")
                continue

            print("Preparing:", symbol)

            df = pd.read_csv(csv_path)
            df = df.dropna().reset_index(drop=True)

            df["ATR_MA50"] = df["ATR14"].rolling(50).mean()
            df["VOLUME_MA50"] = df["volume"].rolling(50).mean()
            df["HIGH_20"] = df["high"].rolling(20).max()

            df = df.dropna().reset_index(drop=True)

            for score, tp_sl, rsi_range, ema_filter, atr_filter, volume_filter, breakout_filter in product(
                self.score_list,
                self.tp_sl_list,
                self.rsi_ranges,
                self.ema_filters,
                self.atr_filter_list,
                self.volume_filter_list,
                self.breakout_filter_list,
            ):
                current += 1
                tp, sl = tp_sl

                print(
                    f"[{current}/{total}] {symbol} "
                    f"Score={score} TP={tp} SL={sl} "
                    f"RSI={rsi_range} VOL={volume_filter} BO={breakout_filter}"
                )

                result = self.backtest(
                    df=df,
                    min_score=score,
                    take_profit_pct=tp,
                    stop_loss_pct=sl,
                    rsi_range=rsi_range,
                    ema_filter=ema_filter,
                    atr_filter=atr_filter,
                    volume_filter=volume_filter,
                    breakout_filter=breakout_filter,
                )

                result.update({
                    "time": datetime.now().isoformat(),
                    "symbol": symbol,
                    "min_score": score,
                    "take_profit_pct": tp,
                    "stop_loss_pct": sl,
                    "rsi_range": str(rsi_range),
                    "ema_filter": ema_filter,
                    "atr_filter": atr_filter,
                    "volume_filter": volume_filter,
                    "breakout_filter": breakout_filter,
                })

                results.append(result)

        if not results:
            print("No results.")
            return

        report = pd.DataFrame(results)

        report = report.sort_values(
            by=["profit_factor_score", "net_profit", "win_rate"],
            ascending=False,
        )

        report.to_csv(self.result_path, index=False)

        best = report[
            (report["trades"] >= 80)
            & (report["net_profit"] > 0)
            & (report["profit_factor_score"] > 1.20)
        ].copy()

        if best.empty:
            best = report.head(30).copy()

        best = best.sort_values(
            by=["profit_factor_score", "net_profit", "win_rate"],
            ascending=False,
        )

        best.to_csv(self.best_path, index=False)

        top = best.iloc[0]

        strategy = {
            "created_at": datetime.now().isoformat(),
            "strategy_name": "TCP_OPTIMIZATION_LAB_V3_FAST",
            "symbol": str(top["symbol"]),
            "timeframe": self.timeframe,
            "min_score": int(top["min_score"]),
            "take_profit_pct": float(top["take_profit_pct"]),
            "stop_loss_pct": float(top["stop_loss_pct"]),
            "rsi_range": str(top["rsi_range"]),
            "ema_filter": str(top["ema_filter"]),
            "atr_filter": bool(top["atr_filter"]),
            "volume_filter": bool(top["volume_filter"]),
            "breakout_filter": bool(top["breakout_filter"]),
            "trades": int(top["trades"]),
            "win_rate": float(top["win_rate"]),
            "net_profit": float(top["net_profit"]),
            "profit_factor": str(top["profit_factor"]),
            "max_drawdown": float(top["max_drawdown"]),
            "expectancy": float(top["expectancy"]),
        }

        self.strategy_path.write_text(
            json.dumps(strategy, indent=4),
            encoding="utf-8"
        )

        print("=" * 70)
        print("OPTIMIZATION LAB V3 FAST - BEST 30")
        print("=" * 70)
        print(best.head(30).to_string(index=False))
        print("=" * 70)
        print("Saved full report ->", self.result_path)
        print("Saved best report ->", self.best_path)
        print("Saved strategy    ->", self.strategy_path)

    def backtest(
        self,
        df,
        min_score,
        take_profit_pct,
        stop_loss_pct,
        rsi_range,
        ema_filter,
        atr_filter,
        volume_filter,
        breakout_filter,
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

                low, high = rsi_range
                rsi = float(row["RSI14"])
                if not (low <= rsi <= high):
                    continue

                if ema_filter == "ema20_gt_ema50_and_ema50_gt_ema200":
                    if not (
                        row["EMA20"] > row["EMA50"]
                        and row["EMA50"] > row["EMA200"]
                    ):
                        continue

                if atr_filter:
                    if row["ATR14"] <= row["ATR_MA50"]:
                        continue

                if volume_filter:
                    if row["volume"] <= row["VOLUME_MA50"]:
                        continue

                if breakout_filter:
                    if row["close"] <= row["HIGH_20"]:
                        continue

                in_position = True
                entry_price = price
                continue

            profit_pct = (price - entry_price) / entry_price

            if profit_pct >= take_profit_pct or profit_pct <= stop_loss_pct:
                profit = (
                    self.balance
                    * self.risk_per_trade
                    * (profit_pct / abs(stop_loss_pct))
                )

                trades.append(round(profit, 4))
                in_position = False

        if not trades:
            return self.empty_result()

        result = pd.DataFrame({"profit": trades})
        result["equity"] = result["profit"].cumsum()
        result["peak"] = result["equity"].cummax()
        result["drawdown"] = result["equity"] - result["peak"]

        wins = result[result["profit"] > 0]
        losses = result[result["profit"] < 0]

        gross_profit = wins["profit"].sum()
        gross_loss = losses["profit"].sum()
        net_profit = result["profit"].sum()

        profit_factor = (
            abs(gross_profit / gross_loss)
            if gross_loss != 0
            else float("inf")
        )

        return {
            "trades": len(result),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(result) * 100, 2),
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

    def empty_result(self):
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


def main():
    OptimizationLabV3().run()


if __name__ == "__main__":
    main()