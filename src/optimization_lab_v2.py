import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from itertools import product

from config.symbols import SYMBOLS
from src.indicator_engine import IndicatorEngine
from src.signal_engine import SignalEngine


class OptimizationLabV2:

    def __init__(self):
        self.timeframe = "15m"
        self.result_path = Path("research/optimization_lab_v2_fast.csv")
        self.best_path = Path("research/optimization_lab_v2_best.csv")
        self.strategy_path = Path("research/best_strategy.json")
        self.result_path.parent.mkdir(parents=True, exist_ok=True)

        self.balance = 5000
        self.risk_per_trade = 0.01

        self.score_list = [60, 70, 80]
        self.tp_sl_list = [
            (0.04, -0.02),
            (0.05, -0.02),
            (0.05, -0.015),
        ]
        self.rsi_ranges = [
            None,
            (30, 70),
            (35, 70),
        ]
        self.ema_filters = [
            "ema50_gt_ema200",
            "ema20_gt_ema50_and_ema50_gt_ema200",
        ]
        self.atr_filter_list = [False, True]
        self.volume_filter_list = [False, True]

    def run(self):
        results = []

        print("=" * 70)
        print("TCP OPTIMIZATION LAB V2 FAST")
        print("=" * 70)

        total_all = (
            len(SYMBOLS)
            * len(self.score_list)
            * len(self.tp_sl_list)
            * len(self.rsi_ranges)
            * len(self.ema_filters)
            * len(self.atr_filter_list)
            * len(self.volume_filter_list)
        )

        current = 0

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

            df["ATR_MA50"] = df["ATR14"].rolling(50).mean()
            df["VOLUME_MA50"] = df["volume"].rolling(50).mean()
            df = df.dropna().reset_index(drop=True)

            for score, tp_sl, rsi_range, ema_filter, atr_filter, volume_filter in product(
                self.score_list,
                self.tp_sl_list,
                self.rsi_ranges,
                self.ema_filters,
                self.atr_filter_list,
                self.volume_filter_list,
            ):
                current += 1
                tp, sl = tp_sl

                print(
                    f"[{current}/{total_all}] {symbol} "
                    f"Score={score} TP={tp} SL={sl} RSI={rsi_range} "
                    f"EMA={ema_filter} ATR={atr_filter} VOL={volume_filter}"
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
            (report["trades"] >= 100)
            & (report["net_profit"] > 0)
            & (report["profit_factor_score"] > 1.20)
        ].copy()

        if best.empty:
            best = report.head(30).copy()
        else:
            best = best.sort_values(
                by=["profit_factor_score", "net_profit", "win_rate"],
                ascending=False,
            )

        best.to_csv(self.best_path, index=False)

        top = best.iloc[0]

        strategy = {
            "created_at": datetime.now().isoformat(),
            "strategy_name": "TCP_OPTIMIZATION_LAB_V2_FAST",
            "symbol": str(top["symbol"]),
            "timeframe": self.timeframe,
            "min_score": int(top["min_score"]),
            "take_profit_pct": float(top["take_profit_pct"]),
            "stop_loss_pct": float(top["stop_loss_pct"]),
            "rsi_range": str(top["rsi_range"]),
            "ema_filter": str(top["ema_filter"]),
            "atr_filter": bool(top["atr_filter"]),
            "volume_filter": bool(top["volume_filter"]),
            "trades": int(top["trades"]),
            "win_rate": float(top["win_rate"]),
            "net_profit": float(top["net_profit"]),
            "profit_factor": str(top["profit_factor"]),
            "max_drawdown": float(top["max_drawdown"]),
            "expectancy": float(top["expectancy"]),
        }

        self.strategy_path.write_text(
            json.dumps(strategy, indent=4),
            encoding="utf-8",
        )

        print("=" * 70)
        print("OPTIMIZATION LAB V2 FAST - BEST 30")
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

                if rsi_range is not None:
                    low, high = rsi_range
                    rsi = float(row["RSI14"])
                    if not (low <= rsi <= high):
                        continue

                if ema_filter == "ema50_gt_ema200":
                    if row["EMA50"] <= row["EMA200"]:
                        continue

                elif ema_filter == "ema20_gt_ema50_and_ema50_gt_ema200":
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
    OptimizationLabV2().run()


if __name__ == "__main__":
    main()