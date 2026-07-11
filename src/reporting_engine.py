from datetime import datetime
from typing import Any, Optional

from src.daily_report_engine import DailyReportEngine
from src.trade_journal_engine import TradeJournalEngine


class ReportingEngine:
    """
    Central reporting coordinator.

    Responsibilities:
    - Record trading events into Trade Journal
    - Refresh Daily Report automatically
    - Refresh Dashboard automatically
    - Send Daily Report to LINE when requested
    """

    def __init__(
        self,
        log_dir: str = "logs",
    ):
        self.journal = TradeJournalEngine(log_dir)
        self.daily_report = DailyReportEngine(log_dir)

        self.last_report: Optional[dict] = None
        self.last_refresh_at: Optional[str] = None

    def record_signal(
        self,
        symbol: str,
        signal: str,
        price: float,
        strategy_score: float,
        reason: str,
        indicators: Optional[dict] = None,
        portfolio_summary: Optional[dict] = None,
    ) -> dict:

        record = self.journal.record(
            event_type="SIGNAL",
            stage="15M_SIGNAL",
            symbol=symbol,
            side=signal,
            decision=signal,
            reason=reason,
            price=price,
            strategy_score=strategy_score,
            indicators=indicators,
            portfolio_summary=portfolio_summary,
        )

        self.refresh(
            portfolio_summary=portfolio_summary,
        )

        return record

    def record_confirmation(
        self,
        symbol: str,
        side: str,
        approved: bool,
        score: float,
        reason: str,
        price: float = 0.0,
        indicators: Optional[dict] = None,
        portfolio_summary: Optional[dict] = None,
    ) -> dict:

        decision = (
            "CONFIRM"
            if approved
            else "WAIT"
        )

        record = self.journal.record(
            event_type=decision,
            stage="5M_CONFIRMATION",
            symbol=symbol,
            side=side,
            decision=decision,
            reason=reason,
            price=price,
            confirmation_score=score,
            indicators=indicators,
            portfolio_summary=portfolio_summary,
        )

        self.refresh(
            portfolio_summary=portfolio_summary,
        )

        return record

    def record_entry_decision(
        self,
        symbol: str,
        side: str,
        approved: bool,
        score: float,
        reason: str,
        price: float,
        portfolio_summary: Optional[dict] = None,
    ) -> dict:

        decision = (
            "EXECUTE"
            if approved
            else "WAIT"
        )

        record = self.journal.record(
            event_type=decision,
            stage="1M_ENTRY",
            symbol=symbol,
            side=side,
            decision=decision,
            reason=reason,
            price=price,
            entry_score=score,
            portfolio_summary=portfolio_summary,
        )

        self.refresh(
            portfolio_summary=portfolio_summary,
        )

        return record

    def record_position_opened(
        self,
        position: Any,
        portfolio_summary: dict,
    ) -> dict:

        record = self.journal.record(
            event_type="POSITION_OPENED",
            stage="POSITION",
            symbol=getattr(position, "symbol", ""),
            side=getattr(position, "side", ""),
            decision="OPEN",
            reason="Position opened",
            price=getattr(
                position,
                "entry_price",
                0.0,
            ),
            strategy_score=getattr(
                position,
                "strategy_score",
                0.0,
            ),
            position=position,
            portfolio_summary=portfolio_summary,
        )

        self.refresh(
            portfolio_summary=portfolio_summary,
        )

        return record

    def record_position_closed(
        self,
        position: Any,
        portfolio_summary: dict,
    ) -> dict:

        record = self.journal.record(
            event_type="POSITION_CLOSED",
            stage="POSITION",
            symbol=getattr(position, "symbol", ""),
            side=getattr(position, "side", ""),
            decision="CLOSE",
            reason=getattr(
                position,
                "exit_reason",
                "",
            ),
            price=getattr(
                position,
                "exit_price",
                0.0,
            ),
            strategy_score=getattr(
                position,
                "strategy_score",
                0.0,
            ),
            position=position,
            portfolio_summary=portfolio_summary,
        )

        self.refresh(
            portfolio_summary=portfolio_summary,
        )

        return record

    def record_risk_rejected(
        self,
        symbol: str,
        side: str,
        reason: str,
        price: float,
        strategy_score: float,
        portfolio_summary: dict,
        metadata: Optional[dict] = None,
    ) -> dict:

        record = self.journal.record(
            event_type="RISK_REJECTED",
            stage="RISK",
            symbol=symbol,
            side=side,
            decision="REJECT",
            reason=reason,
            price=price,
            strategy_score=strategy_score,
            portfolio_summary=portfolio_summary,
            metadata=metadata,
        )

        self.refresh(
            portfolio_summary=portfolio_summary,
        )

        return record

    def record_system_event(
        self,
        event_type: str,
        reason: str,
        metadata: Optional[dict] = None,
        portfolio_summary: Optional[dict] = None,
    ) -> dict:

        record = self.journal.record(
            event_type=event_type,
            stage="SYSTEM",
            decision=event_type,
            reason=reason,
            portfolio_summary=portfolio_summary,
            metadata=metadata,
        )

        self.refresh(
            portfolio_summary=portfolio_summary,
        )

        return record

    def record_execution_event(
        self,
        event: Any,
        portfolio_summary: Optional[dict] = None,
    ) -> dict:

        record = self.journal.record_execution_event(
            event=event,
            portfolio_summary=portfolio_summary,
        )

        self.refresh(
            portfolio_summary=portfolio_summary,
        )

        return record

    def refresh(
        self,
        portfolio_summary: Optional[dict] = None,
        risk_summary: Optional[dict] = None,
        date_text: Optional[str] = None,
    ) -> dict:

        report = self.daily_report.generate(
            date_text=date_text,
            portfolio_summary=portfolio_summary,
            risk_summary=risk_summary,
        )

        self.last_report = report
        self.last_refresh_at = (
            datetime.now().isoformat()
        )

        return report

    def send_daily_line(
        self,
        portfolio_summary: Optional[dict] = None,
        risk_summary: Optional[dict] = None,
        date_text: Optional[str] = None,
    ) -> bool:

        report = self.refresh(
            portfolio_summary=portfolio_summary,
            risk_summary=risk_summary,
            date_text=date_text,
        )

        return self.daily_report.send_line(report)

    def summary(self) -> dict:
        return {
            "last_refresh_at":
                self.last_refresh_at,
            "journal":
                self.journal.summary(),
            "daily_report_available":
                self.last_report is not None,
            "dashboard_file":
                str(
                    self.daily_report.dashboard_html
                ),
        }