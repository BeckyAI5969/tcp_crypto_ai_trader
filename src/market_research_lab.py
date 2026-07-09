import pandas as pd
from pathlib import Path
from datetime import datetime

from config.symbols import SYMBOLS
from src.indicator_engine import IndicatorEngine


class MarketResearchLab:

    def __init__(self):
        self.timeframe = "15m"
        self.output_path = Path("research/market_dataset.csv")
        self.summary_path = Path("research/market_research_summary.txt")

        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        self.forward_bars = [4, 8, 16, 32]
        self.label_threshold = 0.005  # 0.5%

    def run(self):
        all_data = []

        print("=" * 70)
        print("TCP MARKET RESEARCH LAB")
        print("=" * 70)

        for symbol in SYMBOLS:
            csv_path = Path(f"data/{symbol}/{self.timeframe}/{symbol}_{self.timeframe}.csv")

            if not csv_path.exists():
                print(symbol, "CSV not found -> skipped")
                continue

            print("Processing:", symbol)

            indicator = IndicatorEngine(str(csv_path))
            indicator.load_csv()
            indicator.calculate()
            indicator.save()

            df = pd.read_csv(csv_path)
            df = self.prepare_dataset(df, symbol)

            all_data.append(df)

            print(symbol, "rows:", len(df))

        if not all_data:
            print("No market data found.")
            return

        dataset = pd.concat(all_data, ignore_index=True)

        dataset.to_csv(self.output_path, index=False)

        summary = self.create_summary(dataset)
        self.summary_path.write_text(summary, encoding="utf-8")

        print(summary)
        print("Saved dataset ->", self.output_path)
        print("Saved summary ->", self.summary_path)

    def prepare_dataset(self, df, symbol):
        df = df.copy()

        df["symbol"] = symbol
        df["timeframe"] = self.timeframe

        if "open_time" in df.columns:
            df["open_time"] = pd.to_datetime(df["open_time"], errors="coerce")
        else:
            df["open_time"] = pd.NaT

        numeric_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "EMA20",
            "EMA50",
            "EMA200",
            "RSI14",
            "MACD",
            "MACD_SIGNAL",
            "MACD_HIST",
            "ATR14",
            "BB_UPPER",
            "BB_MIDDLE",
            "BB_LOWER",
        ]

        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        volume_ma_col = None
        if "VOLUME_MA20" in df.columns:
            volume_ma_col = "VOLUME_MA20"
        elif "Volume_MA20" in df.columns:
            volume_ma_col = "Volume_MA20"

        if volume_ma_col:
            df[volume_ma_col] = pd.to_numeric(df[volume_ma_col], errors="coerce")
        else:
            df["VOLUME_MA20"] = df["volume"].rolling(20).mean()
            volume_ma_col = "VOLUME_MA20"

        df["ema20_gt_ema50"] = (df["EMA20"] > df["EMA50"]).astype(int)
        df["ema50_gt_ema200"] = (df["EMA50"] > df["EMA200"]).astype(int)
        df["price_gt_ema200"] = (df["close"] > df["EMA200"]).astype(int)

        df["macd_gt_signal"] = (df["MACD"] > df["MACD_SIGNAL"]).astype(int)
        df["macd_hist_positive"] = (df["MACD_HIST"] > 0).astype(int)

        df["volume_gt_ma20"] = (df["volume"] > df[volume_ma_col]).astype(int)

        df["atr_pct"] = df["ATR14"] / df["close"] * 100
        df["bb_width_pct"] = (df["BB_UPPER"] - df["BB_LOWER"]) / df["close"] * 100

        df["rsi_oversold"] = (df["RSI14"] < 35).astype(int)
        df["rsi_neutral"] = ((df["RSI14"] >= 35) & (df["RSI14"] <= 65)).astype(int)
        df["rsi_overbought"] = (df["RSI14"] > 65).astype(int)

        for bars in self.forward_bars:
            df[f"future_close_{bars}"] = df["close"].shift(-bars)
            df[f"future_return_{bars}"] = (
                df[f"future_close_{bars}"] - df["close"]
            ) / df["close"] * 100

        df["label_16"] = "NEUTRAL"
        df.loc[df["future_return_16"] >= self.label_threshold * 100, "label_16"] = "BUY_EDGE"
        df.loc[df["future_return_16"] <= -self.label_threshold * 100, "label_16"] = "SELL_EDGE"

        keep_columns = [
            "symbol",
            "timeframe",
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "EMA20",
            "EMA50",
            "EMA200",
            "RSI14",
            "MACD",
            "MACD_SIGNAL",
            "MACD_HIST",
            "ATR14",
            "BB_UPPER",
            "BB_MIDDLE",
            "BB_LOWER",
            volume_ma_col,
            "ema20_gt_ema50",
            "ema50_gt_ema200",
            "price_gt_ema200",
            "macd_gt_signal",
            "macd_hist_positive",
            "volume_gt_ma20",
            "atr_pct",
            "bb_width_pct",
            "rsi_oversold",
            "rsi_neutral",
            "rsi_overbought",
            "future_return_4",
            "future_return_8",
            "future_return_16",
            "future_return_32",
            "label_16",
        ]

        keep_columns = [col for col in keep_columns if col in df.columns]

        df = df[keep_columns]
        df = df.dropna()

        return df

    def create_summary(self, dataset):
        total_rows = len(dataset)
        symbols = dataset["symbol"].nunique()

        start_date = dataset["open_time"].min()
        end_date = dataset["open_time"].max()

        label_counts = dataset["label_16"].value_counts().to_dict()

        feature_summary = []

        feature_columns = [
            "ema20_gt_ema50",
            "ema50_gt_ema200",
            "price_gt_ema200",
            "macd_gt_signal",
            "macd_hist_positive",
            "volume_gt_ma20",
            "rsi_oversold",
            "rsi_neutral",
            "rsi_overbought",
        ]

        for feature in feature_columns:
            if feature not in dataset.columns:
                continue

            group = dataset.groupby(feature)["future_return_16"].mean().to_dict()

            feature_summary.append(
                f"- {feature}: {group}"
            )

        summary = f"""
======================================================================
TCP MARKET RESEARCH LAB SUMMARY
======================================================================

Generated At     : {datetime.now()}
Symbols Tested   : {symbols}
Total Rows       : {total_rows}
Timeframe        : {self.timeframe}

Backtest Period
Start Date       : {start_date}
End Date         : {end_date}

Forward Labels
Return 4 Bars    : future_return_4
Return 8 Bars    : future_return_8
Return 16 Bars   : future_return_16
Return 32 Bars   : future_return_32

Label Rule
BUY_EDGE         : future_return_16 >= +0.5%
SELL_EDGE        : future_return_16 <= -0.5%
NEUTRAL          : between -0.5% and +0.5%

Label Counts
{label_counts}

Feature Average Future Return 16 Bars
{chr(10).join(feature_summary)}

Files
Dataset          : {self.output_path}
Summary          : {self.summary_path}

======================================================================
"""
        return summary


def main():
    MarketResearchLab().run()


if __name__ == "__main__":
    main()