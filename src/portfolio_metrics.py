import math
import pandas as pd


class PortfolioMetrics:

    @staticmethod
    def profit_factor(trades_df: pd.DataFrame) -> float:
        if trades_df.empty or "profit" not in trades_df.columns:
            return 0.0

        gross_profit = trades_df[trades_df["profit"] > 0]["profit"].sum()
        gross_loss = trades_df[trades_df["profit"] < 0]["profit"].sum()

        if gross_loss == 0:
            return 999999.0 if gross_profit > 0 else 0.0

        return round(abs(gross_profit / gross_loss), 4)

    @staticmethod
    def win_rate(trades_df: pd.DataFrame) -> float:
        if trades_df.empty or "profit" not in trades_df.columns:
            return 0.0

        wins = trades_df[trades_df["profit"] > 0]
        return round(len(wins) / len(trades_df) * 100, 2)

    @staticmethod
    def max_drawdown(equity_df: pd.DataFrame) -> float:
        if equity_df.empty or "equity" not in equity_df.columns:
            return 0.0

        equity = equity_df["equity"]
        peak = equity.cummax()
        drawdown = equity - peak

        return round(drawdown.min(), 2)

    @staticmethod
    def max_drawdown_pct(equity_df: pd.DataFrame) -> float:
        if equity_df.empty or "equity" not in equity_df.columns:
            return 0.0

        equity = equity_df["equity"]
        peak = equity.cummax()
        drawdown_pct = (equity - peak) / peak * 100

        return round(drawdown_pct.min(), 2)

    @staticmethod
    def sharpe_ratio(equity_df: pd.DataFrame) -> float:
        if equity_df.empty or "equity" not in equity_df.columns:
            return 0.0

        returns = equity_df["equity"].pct_change().dropna()

        if returns.empty or returns.std() == 0:
            return 0.0

        return round((returns.mean() / returns.std()) * math.sqrt(252), 4)

    @staticmethod
    def sortino_ratio(equity_df: pd.DataFrame) -> float:
        if equity_df.empty or "equity" not in equity_df.columns:
            return 0.0

        returns = equity_df["equity"].pct_change().dropna()
        downside = returns[returns < 0]

        if returns.empty or downside.std() == 0:
            return 0.0

        return round((returns.mean() / downside.std()) * math.sqrt(252), 4)

    @staticmethod
    def recovery_factor(equity_df: pd.DataFrame, net_profit: float) -> float:
        max_dd = abs(PortfolioMetrics.max_drawdown(equity_df))

        if max_dd == 0:
            return 0.0

        return round(net_profit / max_dd, 4)

    @staticmethod
    def summarize(trades_df: pd.DataFrame, equity_df: pd.DataFrame) -> dict:
        total_trades = len(trades_df)

        if total_trades == 0:
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0,
                "gross_profit": 0,
                "gross_loss": 0,
                "net_profit": 0,
                "profit_factor": 0,
                "max_drawdown": 0,
                "max_drawdown_pct": 0,
                "sharpe_ratio": 0,
                "sortino_ratio": 0,
                "recovery_factor": 0,
                "expectancy": 0,
            }

        wins = trades_df[trades_df["profit"] > 0]
        losses = trades_df[trades_df["profit"] < 0]

        gross_profit = wins["profit"].sum()
        gross_loss = losses["profit"].sum()
        net_profit = trades_df["profit"].sum()

        return {
            "total_trades": total_trades,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": PortfolioMetrics.win_rate(trades_df),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "net_profit": round(net_profit, 2),
            "profit_factor": PortfolioMetrics.profit_factor(trades_df),
            "max_drawdown": PortfolioMetrics.max_drawdown(equity_df),
            "max_drawdown_pct": PortfolioMetrics.max_drawdown_pct(equity_df),
            "sharpe_ratio": PortfolioMetrics.sharpe_ratio(equity_df),
            "sortino_ratio": PortfolioMetrics.sortino_ratio(equity_df),
            "recovery_factor": PortfolioMetrics.recovery_factor(
                equity_df,
                net_profit,
            ),
            "expectancy": round(net_profit / total_trades, 2),
        }