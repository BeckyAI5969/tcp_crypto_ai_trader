from datetime import date, datetime

from src.line_alert import LineAlert
from src.paper_execution import PaperExecutionEngine
from src.paper_portfolio import PaperPortfolio
from src.paper_report import PaperReport
from src.paper_trade_log import PaperTradeLogger
from src.position_manager import PositionManager
from src.position_state_store import PositionStateStore
from src.risk_manager import RiskManager
from src.risk_report import RiskReport


class PaperTrader:

    def __init__(self):
        self.execution = PaperExecutionEngine()
        self.portfolio = PaperPortfolio()
        self.position_manager = PositionManager()

        self.logger = PaperTradeLogger()
        self.paper_report = PaperReport()

        self.risk_manager = RiskManager()
        self.risk_report = RiskReport()

        self.state_store = PositionStateStore()
        self.line_alert = LineAlert()

        self.recovered_positions = 0
        self.last_risk_rejection = None

        self._restore_state()

    def on_signal(
        self,
        symbol,
        signal,
        price,
        score,
        atr=0.0,
    ):
        symbol = symbol.upper()
        signal = signal.upper()

        if signal not in {"BUY", "SELL"}:
            return self.update_market_price(
                symbol=symbol,
                price=price,
            )

        current = self.portfolio.find_open_position(symbol)

        if current is not None:
            return self.update_market_price(
                symbol=symbol,
                price=price,
            )

        portfolio_summary = self.portfolio.summary()

        decision = self.risk_manager.evaluate(
            symbol=symbol,
            side=signal,
            entry_price=price,
            atr=atr,
            strategy_score=score,
            portfolio_summary=portfolio_summary,
        )

        if not decision.approved:
            self.last_risk_rejection = {
                "time": datetime.now().isoformat(),
                "symbol": symbol,
                "signal": signal,
                "price": price,
                "score": score,
                "reason": decision.reason,
                "projected_margin_used":
                    decision.projected_margin_used,
                "projected_margin_usage_pct":
                    decision.projected_margin_usage_pct,
                "projected_open_risk":
                    decision.projected_open_risk,
                "projected_open_risk_pct":
                    decision.projected_open_risk_pct,
            }

            print()
            print("RISK REJECTED")
            print("Symbol :", symbol)
            print("Reason :", decision.reason)
            print()

            self.line_alert.risk_rejected(
                symbol=symbol,
                reason=decision.reason,
                portfolio_summary=portfolio_summary,
            )

            self._save_all()
            return None

        order = self.execution.create_order(
            symbol=symbol,
            signal=signal,
            price=price,
            quantity=decision.quantity,
            score=score,
        )

        position = self.execution.execute_order(
            order=order,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            leverage=decision.leverage,
            required_margin=decision.required_margin,
            risk_amount=decision.risk_amount,
            notional_value=decision.notional_value,
        )

        portfolio_decision = self.portfolio.evaluate_new_position(
            required_margin=position.required_margin,
            risk_amount=position.risk_amount,
        )

        if not portfolio_decision.approved:
            self.last_risk_rejection = {
                "time": datetime.now().isoformat(),
                "symbol": symbol,
                "signal": signal,
                "price": price,
                "score": score,
                "reason": portfolio_decision.reason,
                "projected_margin_used":
                    portfolio_decision.projected_margin_used,
                "projected_margin_usage_pct":
                    portfolio_decision.projected_margin_usage_pct,
                "projected_open_risk":
                    portfolio_decision.projected_open_risk,
                "projected_open_risk_pct":
                    portfolio_decision.projected_open_risk_pct,
            }

            print()
            print("PORTFOLIO RISK REJECTED")
            print("Symbol :", symbol)
            print("Reason :", portfolio_decision.reason)
            print()

            self.line_alert.risk_rejected(
                symbol=symbol,
                reason=portfolio_decision.reason,
                portfolio_summary=self.portfolio.summary(),
            )

            self._save_all()
            return None

        self.portfolio.add_position(position)
        self.logger.log_open(position)

        self.last_risk_rejection = None
        self._save_all()

        self.line_alert.position_opened(
            position=position,
            portfolio_summary=self.portfolio.summary(),
        )

        return position

    def update_market_price(
        self,
        symbol,
        price,
    ):
        symbol = symbol.upper()

        position = self.portfolio.find_open_position(symbol)

        if position is None:
            return None

        result = self.position_manager.update_position(
            position=position,
            price=price,
        )

        if result.action == "UPDATE":
            self.logger.log_update(position)

        elif result.action == "CLOSE":
            self._apply_exit_costs(position)
            self.logger.log_close(position)

            self.risk_manager.update_after_close(
                position.realized_pnl
            )

            self._save_all()

            self.line_alert.position_closed(
                position=position,
                portfolio_summary=self.portfolio.summary(),
            )

            return position

        self._save_all()
        return position

    def close_position(
        self,
        symbol,
        exit_price,
        reason="MANUAL",
    ):
        symbol = symbol.upper()

        position = self.portfolio.find_open_position(symbol)

        if position is None:
            return None

        result = self.position_manager.close_position(
            position=position,
            price=exit_price,
            reason=reason,
        )

        if result.action == "CLOSE":
            self._apply_exit_costs(position)
            self.logger.log_close(position)

            self.risk_manager.update_after_close(
                position.realized_pnl
            )

            self._save_all()

            self.line_alert.position_closed(
                position=position,
                portfolio_summary=self.portfolio.summary(),
            )

            return position

        self._save_all()
        return position

    def _apply_exit_costs(self, position):
        if position.exit_price is None:
            return

        exit_notional = (
            float(position.exit_price)
            * float(position.quantity)
        )

        exit_fee = 0.0

        if self.execution.config.include_trading_fee:
            exit_fee += (
                exit_notional
                * self.execution.config.taker_fee_rate
            )

        if self.execution.config.include_slippage:
            exit_fee += (
                exit_notional
                * self.execution.config.estimated_slippage_rate
            )

        position.exit_fee = round(exit_fee, 8)

        gross_pnl = position._gross_pnl(
            float(position.exit_price)
        )

        position.realized_pnl = round(
            gross_pnl
            - position.entry_fee
            - position.exit_fee
            - position.funding_fee,
            8,
        )

    def save_state(self):
        self.state_store.save(
            positions=self.portfolio.positions,
            risk_manager=self.risk_manager,
        )

    def _save_all(self):
        portfolio_summary = self.portfolio.summary()

        self.paper_report.save(
            self.portfolio,
            self.logger,
        )

        self.risk_report.save(
            self.risk_manager,
            portfolio_summary,
        )

        self.save_state()

    def _restore_state(self):
        state = self.state_store.load()

        restored_positions = state.get(
            "positions",
            [],
        )

        self.portfolio.positions = restored_positions

        self.recovered_positions = len(
            [
                position
                for position in restored_positions
                if position.is_open()
            ]
        )

        risk_state = state.get(
            "risk",
            {},
        )

        state_date = risk_state.get("state_date")
        today = date.today().isoformat()

        if state_date == today:
            self.risk_manager.daily_realized_pnl = float(
                risk_state.get(
                    "daily_realized_pnl",
                    0.0,
                )
            )

            self.risk_manager.consecutive_losses = int(
                risk_state.get(
                    "consecutive_losses",
                    0,
                )
            )

            cooldown_until = risk_state.get(
                "cooldown_until"
            )

            if cooldown_until:
                try:
                    parsed_cooldown = datetime.fromisoformat(
                        cooldown_until
                    )

                    if parsed_cooldown > datetime.now():
                        self.risk_manager.cooldown_until = (
                            parsed_cooldown
                        )

                except ValueError:
                    self.risk_manager.cooldown_until = None

        else:
            self.risk_manager.reset_daily_state()

        if self.recovered_positions > 0:
            print()
            print(
                "RECOVERY:",
                self.recovered_positions,
                "open position(s) restored",
            )

            for position in self.portfolio.get_open_positions():
                print(position.to_dict())

            print()

            self.line_alert.recovery_restored(
                self.recovered_positions
            )

        self._save_all()

    def summary(self):
        summary = self.portfolio.summary()

        summary["recovered_open_positions"] = (
            self.recovered_positions
        )

        summary["last_risk_rejection"] = (
            self.last_risk_rejection
        )

        return summary

    def risk_summary(self):
        result = self.risk_manager.summary()
        result["portfolio_risk"] = (
            self.portfolio.risk_snapshot()
        )
        result["last_risk_rejection"] = (
            self.last_risk_rejection
        )
        return result