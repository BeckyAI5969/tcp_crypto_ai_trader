import json
from pathlib import Path
from datetime import datetime
from itertools import product

import pandas as pd

from config.symbols import SYMBOLS


class OptimizationLabV4:

    def __init__(self):
        self.timeframe = "15m"
        self.result_path = Path("research/optimization_lab_v4.csv")
        self.best_path = Path("research/optimization_lab_v4_best.csv")
        self.strategy_path = Path("research/best_strategy_v4.json")
        self.result_path.parent.mkdir(parents=True, exist_ok=True)

        self.balance = 5000
        self.risk_per_trade = 0.01

        self.score_list = [60, 65, 70]
        self.rsi_ranges = [(30, 55), (30, 60), (35, 60), (35, 65)]
        self.atr_modes = ["sma20", "percentile40"]
        self.volume_multipliers = [1.10, 1.15, 1.20]
        self.ema_confirm_list = [True]
        self.exit_modes = ["fixed", "ema20_exit"]

        self.take_profit_pct = 0.04
        self.stop_loss_pct = -0.02

    def run(self):
        results = []

        print("=" * 70)
        print("TCP OPTIMIZATION LAB V4 - FINAL OPTIMIZATION")
        print("=" * 70)

        total = (
            len(SYMBOLS)
            * len(self.score_list)
            * len(self.rsi_ranges)
            * len(self.atr_modes)
            * len(self.volume_multipliers)
            * len(self.ema_confirm_list)
            * len(self.exit_modes)
        )

        current = 0

        for symbol in SYMBOLS:
            csv_path = Path(f"data/{symbol}/{self.timeframe}/{symbol}_{self.timeframe}.csv")

            if not csv_path.exists():
                print(symbol, "CSV not found -> skipped")
                continue

            df = pd.read_csv(csv_path)
            df = df.dropna().reset_index(drop=True)

            df["ATR_MA20"] = df["ATR14"].rolling(20).mean()
            df["ATR_P40"] = df["ATR14"].rolling(200).quantile(0.40)
            df["VOLUME_MA20"] = df["volume"].rolling(20).mean()
            df = df.dropna().reset_index(drop=True)

            for score, rsi_range, atr_mode, vol_mult, ema_confirm, exit_mode in product(
                self.score_list,
                self.rsi_ranges,
                self.atr_modes,
                self.volume_multipliers,
                self.ema_confirm_list,
                self.exit_modes,
            ):
                current += 1

                print(
                    f"[{current}/{total}] {symbol} "
                    f"Score={score} RSI={rsi_range} ATR={atr_mode} "
                    f"VOLx={vol_mult} Exit={exit_mode}"
                )

                result = self.backtest(
                    df=df,
                    min_score=score,
                    rsi_range=rsi_range,
                    atr_mode=atr_mode,
                    volume_multiplier=vol_mult,
                    ema_confirm=ema_confirm,
                    exit_mode=exit_mode,
                )

                result.update({
                    "time": datetime.now().isoformat(),
                    "symbol": symbol,
                    "min_score": score,
                    "rsi_range": str(rsi_range),
                    "atr_mode": atr_mode,
                    "volume_multiplier": vol_mult,
                    "ema_confirm": ema_confirm,
                    "exit_mode": exit_mode,
                    "take_profit_pct": self.take_profit_pct,
                    "stop_loss_pct": self.stop_loss_pct,
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
            & (report["profit_factor_score"] > 1.25)
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
            "strategy_name": "TCP_FINAL_OPTIMIZATION_V4",
            "symbol": str(top["symbol"]),
            "timeframe": self.timeframe,
            "min_score": int(top["min_score"]),
            "rsi_range": str(top["rsi_range"]),
            "atr_mode": str(top["atr_mode"]),
            "volume_multiplier": float(top["volume_multiplier"]),
            "ema_confirm": bool(top["ema_confirm"]),
            "exit_mode": str(top["exit_mode"]),
            "take_profit_pct": float(top["take_profit_pct"]),
            "stop_loss_pct": float(top["stop_loss_pct"]),
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
        print("OPTIMIZATION LAB V4 - BEST 30")
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
        rsi_range,
        atr_mode,
        volume_multiplier,
        ema_confirm,
        exit_mode,
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

                rsi_low, rsi_high = rsi_range
                rsi = float(row["RSI14"])
                if not (rsi_low <= rsi <= rsi_high):
                    continue

                if not (row["EMA50"] > row["EMA200"]):
                    continue

                if ema_confirm:
                    if i < 2:
                        continue
                    if not (
                        df.iloc[i]["close"] > df.iloc[i]["EMA20"]
                        and df.iloc[i - 1]["close"] > df.iloc[i - 1]["EMA20"]
                    ):
                        continue

                if atr_mode == "sma20":
                    if row["ATR14"] <= row["ATR_MA20"]:
                        continue

                elif atr_mode == "percentile40":
                    if row["ATR14"] <= row["ATR_P40"]:
                        continue

                if row["volume"] <= row["VOLUME_MA20"] * volume_multiplier:
                    continue

                in_position = True
                entry_price = price
                continue

            profit_pct = (price - entry_price) / entry_price

            exit_signal = (
                profit_pct >= self.take_profit_pct
                or profit_pct <= self.stop_loss_pct
            )

            if exit_mode == "ema20_exit":
                if row["close"] < row["EMA20"] and profit_pct > 0:
                    exit_signal = True

            if exit_signal:
                profit = (
                    self.balance
                    * self.risk_per_trade
                    * (profit_pct / abs(self.stop_loss_pct))
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

        pf = abs(gross_profit / gross_loss) if gross_loss != 0 else float("inf")

        return {
            "trades": len(result),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(result) * 100, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "net_profit": round(net_profit, 2),
            "profit_factor": round(pf, 4) if pf != float("inf") else "Infinity",
            "profit_factor_score": pf if pf != float("inf") else 999999,
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
    OptimizationLabV4().run()


if __name__ == "__main__":
    main()