import pandas as pd
from pathlib import Path
from datetime import datetime

from src.optimizer_engine import OptimizerEngine


class WalkForwardEngine:

    def __init__(self, csv_path="data/BTCUSDT/15m/BTCUSDT_15m.csv"):
        self.csv_path = Path(csv_path)
        self.result_path = Path("logs/walk_forward_results.csv")
        self.result_path.parent.mkdir(parents=True, exist_ok=True)

    def run(self):
        df = pd.read_csv(self.csv_path)

        split_index = int(len(df) * 0.7)

        train_df = df.iloc[:split_index].copy()
        test_df = df.iloc[split_index:].copy()

        print("=" * 60)
        print("Walk Forward Validation")
        print("=" * 60)
        print("Total Rows :", len(df))
        print("Train Rows :", len(train_df))
        print("Test Rows  :", len(test_df))
        print("=" * 60)

        optimizer = OptimizerEngine()

        best_result = None

        for ema_w in optimizer.ema_weights:
            for rsi_w in optimizer.rsi_weights:
                for macd_w in optimizer.macd_weights:
                    for volume_w in optimizer.volume_weights:
                        for atr_w in optimizer.atr_weights:

                            total = ema_w + rsi_w + macd_w + volume_w + atr_w

                            if round(total, 2) != 1.00:
                                continue

                            train_signal = optimizer.generate_signals(
                                train_df.copy(),
                                ema_w,
                                rsi_w,
                                macd_w,
                                volume_w,
                                atr_w
                            )

                            train_result = optimizer.backtest(train_signal)

                            if best_result is None or train_result["net_profit"] > best_result["net_profit"]:
                                best_result = train_result
                                best_result["weights"] = {
                                    "ema": ema_w,
                                    "rsi": rsi_w,
                                    "macd": macd_w,
                                    "volume": volume_w,
                                    "atr": atr_w
                                }

        weights = best_result["weights"]

        test_signal = optimizer.generate_signals(
            test_df.copy(),
            weights["ema"],
            weights["rsi"],
            weights["macd"],
            weights["volume"],
            weights["atr"]
        )

        test_result = optimizer.backtest(test_signal)

        final_result = {
            "time": datetime.now().isoformat(),
            "train_trades": best_result["trades"],
            "train_win_rate": best_result["win_rate"],
            "train_net_profit": best_result["net_profit"],
            "test_trades": test_result["trades"],
            "test_win_rate": test_result["win_rate"],
            "test_net_profit": test_result["net_profit"],
            "test_profit_factor": test_result["profit_factor"],
            "test_expectancy": test_result["expectancy"],
            "test_max_drawdown": test_result["max_drawdown"],
            "ema": weights["ema"],
            "rsi": weights["rsi"],
            "macd": weights["macd"],
            "volume": weights["volume"],
            "atr": weights["atr"]
        }

        result_df = pd.DataFrame([final_result])
        result_df.to_csv(self.result_path, index=False)

        print("Best Train Result:")
        print(best_result)
        print("=" * 60)
        print("Out-of-Sample Test Result:")
        print(test_result)
        print("=" * 60)
        print("Saved ->", self.result_path)


def main():
    engine = WalkForwardEngine()
    engine.run()


if __name__ == "__main__":
    main()