import pandas as pd
from pathlib import Path


def main():
    source = Path("research/optimization_lab_v4.csv")
    output = Path("research/coin_comparison_report_v4.csv")

    if not source.exists():
        print("File not found:", source)
        return

    df = pd.read_csv(source)

    df = df[
        (df["trades"] >= 50)
        & (df["net_profit"] > 0)
    ]

    best_by_coin = (
        df.sort_values(
            by=["profit_factor_score", "net_profit", "win_rate"],
            ascending=False
        )
        .groupby("symbol")
        .head(1)
        .sort_values(
            by=["profit_factor_score", "net_profit"],
            ascending=False
        )
    )

    best_by_coin.to_csv(output, index=False)

    print("=" * 100)
    print("COIN COMPARISON REPORT V4")
    print("=" * 100)

    cols = [
        "symbol",
        "trades",
        "win_rate",
        "net_profit",
        "profit_factor",
        "max_drawdown",
        "expectancy",
        "min_score",
        "rsi_range",
        "atr_mode",
        "volume_multiplier",
        "exit_mode",
        "take_profit_pct",
        "stop_loss_pct",
    ]

    print(best_by_coin[cols].to_string(index=False))

    print("=" * 100)
    print("Best Coin:", best_by_coin.iloc[0]["symbol"])
    print("Best PF  :", best_by_coin.iloc[0]["profit_factor"])
    print("Saved ->", output)
    print("=" * 100)


if __name__ == "__main__":
    main()