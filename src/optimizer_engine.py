import itertools
import pandas as pd
from pathlib import Path
from datetime import datetime


class OptimizerEngine:

    def __init__(self, csv_path="data/BTCUSDT/15m/BTCUSDT_15m.csv"):
        self.csv_path = Path(csv_path)
        self.result_path = Path("logs/optimizer_results.csv")
        self.result_path.parent.mkdir(parents=True, exist_ok=True)

        self.ema_weights = [0.25, 0.30, 0.35, 0.40]
        self.rsi_weights = [0.15, 0.20, 0.25]
        self.macd_weights = [0.20, 0.25, 0.30]
        self.volume_weights = [0.05, 0.10, 0.15]
        self.atr_weights = [0.05, 0.10, 0.15]

    def run(self):
        df = pd.read_csv(self.csv_path)

        all_results = []
        best_result = None

        combinations = itertools.product(
            self.ema_weights,
            self.rsi_weights,
            self.macd_weights,
            self.volume_weights,
            self.atr_weights
        )

        for ema_w, rsi_w, macd_w, volume_w, atr_w in combinations:
            if round(ema_w + rsi_w + macd_w + volume_w + atr_w, 2) != 1.00:
                continue

            test_df = self.generate_signals(
                df.copy(),
                ema_w,
                rsi_w,
                macd_w,
                volume_w,
                atr_w
            )

            result = self.backtest(test_df)

            result.update({
                "time": datetime.now().isoformat(),
                "ema": ema_w,
                "rsi": rsi_w,
                "macd": macd_w,
                "volume": volume_w,
                "atr": atr_w
            })

            all_results.append(result)

            if best_result is None or result["net_profit"] > best_result["net_profit"]:
                best_result = result

        results_df = pd.DataFrame(all_results)
        results_df.to_csv(self.result_path, index=False)

        print("=" * 60)
        print("Optimizer Result")
        print("=" * 60)
        print(best_result)
        print("Saved ->", self.result_path)
        print("=" * 60)

    def generate_signals(self, df, ema_w, rsi_w, macd_w, volume_w, atr_w):
        ema_score = (df["EMA20"] > df["EMA50"]).astype(int)

        rsi_score = (
            (df["RSI14"] > 45) &
            (df["RSI14"] < 65)
        ).astype(int)

        macd_score = (
            df["MACD"] > 0
        ).astype(int) if "MACD" in df.columns else 0

        volume_score = (
            df["volume"] > df["Volume_MA20"]
        ).astype(int) if "Volume_MA20" in df.columns else 1

        atr_score = (
            df["ATR14"] > 0
        ).astype(int) if "ATR14" in df.columns else 1

        df["AI_SCORE"] = (
            ema_score * ema_w +
            rsi_score * rsi_w +
            macd_score * macd_w +
            volume_score * volume_w +
            atr_score * atr_w
        ) * 100

        df["Signal"] = "WAIT"
        df.loc[df["AI_SCORE"] >= 80, "Signal"] = "BUY"
        df.loc[df["AI_SCORE"] <= 20, "Signal"] = "SELL"

        return df

    def backtest(self, df):
        balance = 5000
        risk_per_trade = 0.01

        trades = []
        holding_bars = []

        in_position = False
        entry_price = 0
        entry_index = 0

        for i in range(len(df)):
            row = df.iloc[i]
            price = float(row["close"])
            signal = str(row.get("Signal", "WAIT"))

            if not in_position and signal == "BUY":
                in_position = True
                entry_price = price
                entry_index = i

            elif in_position:
                profit_percent = (price - entry_price) / entry_price

                if profit_percent >= 0.02 or profit_percent <= -0.01:
                    profit = balance * risk_per_trade * (profit_percent / 0.01)
                    trades.append(profit)
                    holding_bars.append(i - entry_index)
                    in_position = False

        if not trades:
            return {
                "trades": 0,
                "win_rate": 0,
                "net_profit": 0,
                "profit_factor": 0,
                "expectancy": 0,
                "avg_holding_bars": 0,
                "max_drawdown": 0
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
        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else "Infinity"
        expectancy = result["profit"].mean()
        avg_holding_bars = sum(holding_bars) / len(holding_bars)
        max_drawdown = result["drawdown"].min()

        return {
            "trades": len(result),
            "win_rate": round(win_rate, 2),
            "net_profit": round(net_profit, 2),
            "profit_factor": profit_factor,
            "expectancy": round(expectancy, 2),
            "avg_holding_bars": round(avg_holding_bars, 2),
            "max_drawdown": round(max_drawdown, 2)
        }


def main():
    engine = OptimizerEngine()
    engine.run()


if __name__ == "__main__":
    main()