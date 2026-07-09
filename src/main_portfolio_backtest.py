from pathlib import Path

from src.portfolio_backtest_engine import PortfolioBacktestEngine
from src.portfolio_trade_executor import PortfolioTradeExecutor
from src.portfolio_statistics import PortfolioStatistics
from src.portfolio_report import PortfolioReport


def main():

    report_path = Path("research/coin_comparison_report_v4.csv")

    if not report_path.exists():
        print("File not found:", report_path)
        return

    engine = PortfolioBacktestEngine()

    executor = PortfolioTradeExecutor(engine)

    trades_df, equity_df = executor.execute_from_coin_report(
        report_path
    )

    statistics = PortfolioStatistics(
        trades_df,
        equity_df,
    ).calculate()

    PortfolioReport().save(
        trades_df,
        equity_df,
        statistics,
    )

    print("\n")
    print("=" * 70)
    print("SPRINT 9 COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()