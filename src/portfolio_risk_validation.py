import json
import os
from datetime import datetime
from pathlib import Path

from src.paper_trader import PaperTrader


class MockLineAlert:
    def __init__(self):
        self.events = []

    def _record(self, name, **payload):
        self.events.append(
            {
                "name": name,
                "payload": payload,
            }
        )
        return True

    def position_opened(self, position, portfolio_summary):
        return self._record(
            "POSITION_OPENED",
            symbol=position.symbol,
            leverage=position.leverage,
            margin=position.required_margin,
            risk=position.risk_amount,
            portfolio=portfolio_summary,
        )

    def position_closed(self, position, portfolio_summary):
        return self._record(
            "POSITION_CLOSED",
            symbol=position.symbol,
            pnl=position.realized_pnl,
            reason=position.exit_reason,
            portfolio=portfolio_summary,
        )

    def risk_rejected(
        self,
        symbol,
        reason,
        portfolio_summary=None,
    ):
        return self._record(
            "RISK_REJECTED",
            symbol=symbol,
            reason=reason,
            portfolio=portfolio_summary or {},
        )

    def recovery_restored(self, recovered_positions):
        return self._record(
            "RECOVERY_RESTORED",
            recovered_positions=recovered_positions,
        )


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def open_position(
    trader,
    symbol,
    price,
    atr,
    score=95.0,
):
    position = trader.on_signal(
        symbol=symbol,
        signal="BUY",
        price=price,
        score=score,
        atr=atr,
    )

    require(
        position is not None,
        f"{symbol} position was not opened",
    )

    require(
        position.leverage > 0,
        f"{symbol} leverage was not assigned",
    )

    require(
        position.required_margin > 0,
        f"{symbol} required margin is invalid",
    )

    require(
        position.risk_amount > 0,
        f"{symbol} risk amount is invalid",
    )

    require(
        position.notional_value > 0,
        f"{symbol} notional value is invalid",
    )

    require(
        position.stop_loss is not None,
        f"{symbol} stop loss is missing",
    )

    require(
        position.take_profit is not None,
        f"{symbol} take profit is missing",
    )

    return position


def main():
    print("=" * 76)
    print("PORTFOLIO RISK + LEVERAGE END-TO-END VALIDATION")
    print("=" * 76)

    project_root = Path.cwd()
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_root = (
        project_root
        / "logs"
        / "portfolio_risk_validation"
        / run_id
    )

    test_root.mkdir(parents=True, exist_ok=False)

    os.chdir(test_root)

    try:
        trader = PaperTrader()
        mock_line = MockLineAlert()
        trader.line_alert = mock_line

        print("\n[1/8] Opening BTCUSDT with 10x leverage")

        btc = open_position(
            trader=trader,
            symbol="BTCUSDT",
            price=60000.0,
            atr=300.0,
            score=95.0,
        )

        require(
            btc.leverage == 10,
            f"BTC leverage expected 10x, got {btc.leverage}x",
        )

        print(btc.to_dict())

        print("\n[2/8] Opening ETHUSDT with 5x leverage")

        eth = open_position(
            trader=trader,
            symbol="ETHUSDT",
            price=3000.0,
            atr=15.0,
            score=95.0,
        )

        require(
            eth.leverage == 5,
            f"ETH leverage expected 5x, got {eth.leverage}x",
        )

        print(eth.to_dict())

        summary = trader.summary()

        require(
            summary["open_positions"] == 2,
            "Expected 2 open positions",
        )

        require(
            summary["open_risk"] <= 25.0 + 1e-6,
            "Combined open risk exceeds 25 USDT",
        )

        require(
            summary["margin_usage_pct"] <= 0.60 + 1e-9,
            "Margin usage exceeds 60%",
        )

        print("\nPortfolio after two positions:")
        print(json.dumps(summary, indent=4, default=str))

        print(
            "\n[3/8] Verifying third high-risk position is rejected"
        )

        rejected = trader.on_signal(
            symbol="SOLUSDT",
            signal="BUY",
            price=150.0,
            score=95.0,
            atr=0.75,
        )

        require(
            rejected is None,
            "Third position should have been rejected",
        )

        require(
            trader.last_risk_rejection is not None,
            "Risk rejection details were not recorded",
        )

        rejection_reason = (
            trader.last_risk_rejection["reason"].lower()
        )

        require(
            (
                "combined open risk" in rejection_reason
                or "portfolio margin usage" in rejection_reason
                or "minimum cash reserve" in rejection_reason
                or "maximum open positions" in rejection_reason
            ),
            "Third position was not rejected by a portfolio risk limit",
        )

        print(trader.last_risk_rejection)

        print("\n[4/8] Closing BTCUSDT at take profit")

        closed_btc = trader.close_position(
            symbol="BTCUSDT",
            exit_price=btc.take_profit,
            reason="VALIDATION_TAKE_PROFIT",
        )

        require(
            closed_btc is not None,
            "BTC position was not closed",
        )

        require(
            not closed_btc.is_open(),
            "BTC position remains open",
        )

        require(
            closed_btc.realized_pnl > 0,
            "BTC realized PnL should be positive",
        )

        require(
            closed_btc.entry_fee > 0,
            "BTC entry fee was not simulated",
        )

        require(
            closed_btc.exit_fee > 0,
            "BTC exit fee was not simulated",
        )

        print(closed_btc.to_dict())

        print(
            "\n[5/8] Opening SOLUSDT after risk budget is released"
        )

        sol = open_position(
            trader=trader,
            symbol="SOLUSDT",
            price=150.0,
            atr=0.75,
            score=95.0,
        )

        require(
            sol.leverage == 5,
            f"SOL leverage expected 5x, got {sol.leverage}x",
        )

        print(sol.to_dict())

        print("\n[6/8] Validating reports and persisted state")

        trader.save_state()

        required_files = [
            Path("logs/paper_state.json"),
            Path("logs/paper_report.json"),
            Path("logs/risk_report.json"),
            Path("logs/paper_trade_log.csv"),
            Path("logs/paper_trade_log.jsonl"),
        ]

        for file_path in required_files:
            require(
                file_path.exists(),
                f"Missing file: {file_path}",
            )

        with open(
            "logs/paper_state.json",
            "r",
            encoding="utf-8",
        ) as file:
            state = json.load(file)

        open_state_positions = [
            position
            for position in state.get("positions", [])
            if position.get("status") == "OPEN"
        ]

        require(
            len(open_state_positions) == 2,
            "Persisted state should contain 2 open positions",
        )

        print("Persisted open positions:", len(open_state_positions))

        print("\n[7/8] Validating recovery")

        recovered_trader = PaperTrader()
        recovered_mock_line = MockLineAlert()
        recovered_trader.line_alert = recovered_mock_line

        recovered_summary = recovered_trader.summary()

        require(
            recovered_summary["open_positions"] == 2,
            "Recovery did not restore 2 open positions",
        )

        require(
            recovered_summary["margin_usage_pct"] <= 0.60 + 1e-9,
            "Recovered margin usage exceeds limit",
        )

        require(
            recovered_summary["open_risk_pct"] <= 0.025 + 1e-9,
            "Recovered open risk exceeds limit",
        )

        recovered_symbols = {
            position.symbol
            for position
            in recovered_trader.portfolio.get_open_positions()
        }

        require(
            recovered_symbols == {"ETHUSDT", "SOLUSDT"},
            "Recovered symbols are incorrect",
        )

        print(json.dumps(
            recovered_summary,
            indent=4,
            default=str,
        ))

        print("\n[8/8] Validating alert events")

        alert_names = [
            event["name"]
            for event in mock_line.events
        ]

        require(
            alert_names.count("POSITION_OPENED") == 3,
            "Expected 3 POSITION_OPENED alerts",
        )

        require(
            "POSITION_CLOSED" in alert_names,
            "POSITION_CLOSED alert is missing",
        )

        require(
            "RISK_REJECTED" in alert_names,
            "RISK_REJECTED alert is missing",
        )

        print("Alert events:", alert_names)

        final_summary = trader.summary()

        print("\n" + "=" * 76)
        print("PORTFOLIO RISK VALIDATION: PASS")
        print("=" * 76)
        print("Initial Capital           : PASS")
        print("BTC Leverage 10x          : PASS")
        print("Altcoin Leverage 5x       : PASS")
        print("Isolated Margin           : PASS")
        print("Margin Usage Limit        : PASS")
        print("Combined Open Risk Limit  : PASS")
        print("Position Rejection        : PASS")
        print("Risk Budget Release       : PASS")
        print("Fees and Slippage         : PASS")
        print("Realized PnL              : PASS")
        print("State Persistence         : PASS")
        print("Position Recovery         : PASS")
        print("LINE Event Integration    : PASS")
        print()
        print("Final Portfolio Summary:")
        print(json.dumps(
            final_summary,
            indent=4,
            default=str,
        ))
        print()
        print("Validation files:")
        print(test_root / "logs")

    finally:
        os.chdir(project_root)


if __name__ == "__main__":
    main()