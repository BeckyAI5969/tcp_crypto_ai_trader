import pandas as pd
from pathlib import Path


class PortfolioBacktestReport:

    def __init__(self):
        self.source_path = Path("research/coin_comparison_report_v4.csv")
        self.output_path = Path("research/portfolio_backtest_report.csv")
        self.summary_path = Path("research/portfolio_backtest_summary.txt")

    def run(self):
        if not self.source_path.exists():
            print("File not found:", self.source_path)
            return

        df = pd.read_csv(self.source_path)

        total_trades = int(df["trades"].sum())
        total_wins = int(df["wins"].sum())
        total_losses = int(df["losses"].sum())

        gross_profit = df["gross_prof"].sum() if "gross_prof" in df.columns else df["gross_profit"].sum()
        gross_loss = df["gross_loss"].sum()
        net_profit = df["net_profit"].sum()

        portfolio_pf = abs(gross_profit / gross_loss) if gross_loss != 0 else 0
        portfolio_win_rate = total_wins / total_trades * 100 if total_trades else 0
        max_drawdown = df["max_draw"].sum() if "max_draw" in df.columns else df["max_drawdown"].sum()
        expectancy = net_profit / total_trades if total_trades else 0

        report = df.copy()
        report["weight_by_pf"] = report["profit_factor"] / report["profit_factor"].sum()
        report["weight_by_profit"] = report["net_profit"] / report["net_profit"].sum()

        report.to_csv(self.output_path, index=False)

        summary = f"""
============================================================
TCP PORTFOLIO BACKTEST REPORT
============================================================

Symbols Tested     : {len(df)}
Total Trades       : {total_trades}
Total Wins         : {total_wins}
Total Losses       : {total_losses}

Gross Profit       : {round(gross_profit, 2)}
Gross Loss         : {round(gross_loss, 2)}
Net Profit         : {round(net_profit, 2)}

Portfolio PF       : {round(portfolio_pf, 4)}
Portfolio Win Rate : {round(portfolio_win_rate, 2)}%
Portfolio DD Sum   : {round(max_drawdown, 2)}
Expectancy         : {round(expectancy, 2)}

Best Symbol by PF  : {df.sort_values("profit_factor", ascending=False).iloc[0]["symbol"]}
Best Symbol Profit : {df.sort_values("net_profit", ascending=False).iloc[0]["symbol"]}

Files
CSV Report         : {self.output_path}
Summary            : {self.summary_path}

============================================================
"""
        self.summary_path.write_text(summary, encoding="utf-8")

        print(summary)
        print(report.to_string(index=False))


def main():
    PortfolioBacktestReport().run()


if __name__ == "__main__":
    main()