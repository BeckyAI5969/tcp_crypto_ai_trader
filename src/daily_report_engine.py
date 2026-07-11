import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from src.line_alert import LineAlert
from src.trade_journal_engine import TradeJournalEngine


class DailyReportEngine:

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.journal = TradeJournalEngine(log_dir)
        self.line_alert = LineAlert()

        self.daily_json = self.log_dir / "daily_report.json"
        self.daily_history = (
            self.log_dir / "daily_report_history.jsonl"
        )
        self.dashboard_html = (
            self.log_dir / "dashboard.html"
        )

    def generate(
        self,
        date_text: Optional[str] = None,
        portfolio_summary: Optional[dict] = None,
        risk_summary: Optional[dict] = None,
    ) -> dict:

        date_text = (
            date_text
            or datetime.now().date().isoformat()
        )

        portfolio_summary = portfolio_summary or {}
        risk_summary = risk_summary or {}

        frame = self.journal.daily_records(date_text)

        closes = self._event_rows(
            frame,
            {"CLOSE", "POSITION_CLOSED"},
        )
        opens = self._event_rows(
            frame,
            {"EXECUTE", "POSITION_OPENED"},
        )
        rejections = self._event_rows(
            frame,
            {"REJECT", "RISK_REJECTED"},
        )

        pnl = self._numeric_series(
            closes,
            "realized_pnl",
        )

        wins = int((pnl > 0).sum())
        losses = int((pnl < 0).sum())
        breakeven = int((pnl == 0).sum())
        closed_trades = int(len(pnl))

        gross_profit = float(pnl[pnl > 0].sum())
        gross_loss = float(pnl[pnl < 0].sum())
        net_pnl = float(pnl.sum())

        win_rate = (
            wins / closed_trades * 100
            if closed_trades > 0
            else 0.0
        )
        profit_factor = (
            gross_profit / abs(gross_loss)
            if gross_loss < 0
            else 0.0
        )
        expectancy = (
            net_pnl / closed_trades
            if closed_trades > 0
            else 0.0
        )

        holding = self._numeric_series(
            closes,
            "holding_seconds",
        )
        average_holding_seconds = (
            float(holding.mean())
            if not holding.empty
            else 0.0
        )

        report = {
            "date": date_text,
            "generated_at": datetime.now().isoformat(),
            "mode": "PAPER_LEVERAGED",
            "journal": self.journal.summary(date_text),
            "performance": {
                "opened_positions": int(len(opens)),
                "closed_trades": closed_trades,
                "wins": wins,
                "losses": losses,
                "breakeven": breakeven,
                "win_rate_pct": round(win_rate, 4),
                "gross_profit": round(gross_profit, 8),
                "gross_loss": round(gross_loss, 8),
                "net_pnl": round(net_pnl, 8),
                "profit_factor": round(
                    profit_factor,
                    8,
                ),
                "expectancy_per_trade": round(
                    expectancy,
                    8,
                ),
                "average_holding_seconds": round(
                    average_holding_seconds,
                    2,
                ),
                "rejections": int(len(rejections)),
            },
            "portfolio": portfolio_summary,
            "risk": risk_summary,
        }

        self._save_json(report)
        self._append_history(report)
        self._save_dashboard(report)

        return report

    def send_line(self, report: dict) -> bool:
        performance = report.get(
            "performance",
            {},
        )
        portfolio = report.get(
            "portfolio",
            {},
        )

        message = (
            "📊 DAILY TRADING REPORT\n"
            f"Date: {report.get('date', '')}\n"
            f"Opened: "
            f"{performance.get('opened_positions', 0)}\n"
            f"Closed: "
            f"{performance.get('closed_trades', 0)}\n"
            f"Wins: {performance.get('wins', 0)}\n"
            f"Losses: {performance.get('losses', 0)}\n"
            f"Win Rate: "
            f"{performance.get('win_rate_pct', 0):.2f}%\n"
            f"Net PnL: "
            f"{performance.get('net_pnl', 0):.4f} USDT\n"
            f"Profit Factor: "
            f"{performance.get('profit_factor', 0):.4f}\n"
            f"Equity: "
            f"{portfolio.get('equity', 0):.4f} USDT\n"
            f"Margin Usage: "
            f"{portfolio.get('margin_usage_pct', 0) * 100:.2f}%\n"
            f"Open Risk: "
            f"{portfolio.get('open_risk_pct', 0) * 100:.2f}%"
        )

        return self.line_alert.send(message)

    def _save_json(self, report: dict):
        temporary = self.daily_json.with_suffix(
            ".json.tmp"
        )

        with open(
            temporary,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False,
                default=str,
            )

        temporary.replace(self.daily_json)

    def _append_history(self, report: dict):
        with open(
            self.daily_history,
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    report,
                    ensure_ascii=False,
                    default=str,
                )
                + "\n"
            )

    def _save_dashboard(self, report: dict):
        performance = report.get(
            "performance",
            {},
        )
        portfolio = report.get(
            "portfolio",
            {},
        )
        journal = report.get(
            "journal",
            {},
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TCP Crypto AI Trader Dashboard</title>
<style>
body {{ font-family: Arial, sans-serif; background: #111827; color: #f9fafb; margin: 0; padding: 24px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 16px; }}
.card {{ background: #1f2937; border-radius: 14px; padding: 18px; }}
.label {{ color: #9ca3af; font-size: 13px; }}
.value {{ font-size: 28px; font-weight: 700; margin-top: 8px; }}
.section {{ margin-top: 28px; }}
</style>
</head>
<body>
<h1>TCP Crypto AI Trader</h1>
<p>Updated: {report.get("generated_at", "")}</p>

<div class="section">
<h2>Daily Performance — {report.get("date", "")}</h2>
<div class="grid">
<div class="card"><div class="label">Net PnL</div><div class="value">{performance.get("net_pnl", 0):.4f} USDT</div></div>
<div class="card"><div class="label">Win Rate</div><div class="value">{performance.get("win_rate_pct", 0):.2f}%</div></div>
<div class="card"><div class="label">Profit Factor</div><div class="value">{performance.get("profit_factor", 0):.4f}</div></div>
<div class="card"><div class="label">Closed Trades</div><div class="value">{performance.get("closed_trades", 0)}</div></div>
</div>
</div>

<div class="section">
<h2>Portfolio</h2>
<div class="grid">
<div class="card"><div class="label">Equity</div><div class="value">{portfolio.get("equity", 0):.4f}</div></div>
<div class="card"><div class="label">Margin Used</div><div class="value">{portfolio.get("margin_used", 0):.4f}</div></div>
<div class="card"><div class="label">Margin Usage</div><div class="value">{portfolio.get("margin_usage_pct", 0) * 100:.2f}%</div></div>
<div class="card"><div class="label">Open Risk</div><div class="value">{portfolio.get("open_risk_pct", 0) * 100:.2f}%</div></div>
</div>
</div>

<div class="section">
<h2>Journal</h2>
<div class="grid">
<div class="card"><div class="label">Signals</div><div class="value">{journal.get("signals", 0)}</div></div>
<div class="card"><div class="label">Confirmations</div><div class="value">{journal.get("confirmations", 0)}</div></div>
<div class="card"><div class="label">Entries</div><div class="value">{journal.get("entries", 0)}</div></div>
<div class="card"><div class="label">Rejections</div><div class="value">{journal.get("rejections", 0)}</div></div>
</div>
</div>
</body>
</html>
"""

        self.dashboard_html.write_text(
            html,
            encoding="utf-8",
        )

    @staticmethod
    def _event_rows(
        frame: pd.DataFrame,
        names: set[str],
    ) -> pd.DataFrame:

        if frame.empty:
            return frame

        values = (
            frame["event_type"]
            .astype(str)
            .str.upper()
        )

        return frame[
            values.isin(names)
        ].copy()

    @staticmethod
    def _numeric_series(
        frame: pd.DataFrame,
        column: str,
    ) -> pd.Series:

        if (
            frame.empty
            or column not in frame.columns
        ):
            return pd.Series(
                dtype="float64"
            )

        return pd.to_numeric(
            frame[column],
            errors="coerce",
        ).fillna(0.0)


def main():
    engine = DailyReportEngine()
    report = engine.generate()

    print(json.dumps(
        report,
        indent=4,
        ensure_ascii=False,
        default=str,
    ))


if __name__ == "__main__":
    main()