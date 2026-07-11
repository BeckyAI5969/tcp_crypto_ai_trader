import os
from typing import Optional

import requests
from dotenv import load_dotenv


class LineAlert:

    def __init__(
        self,
        timeout_seconds: int = 10,
    ):
        load_dotenv()

        self.token = os.getenv(
            "LINE_CHANNEL_ACCESS_TOKEN"
        )

        self.user_id = os.getenv(
            "LINE_USER_ID"
        )

        self.timeout_seconds = timeout_seconds
        self.endpoint = (
            "https://api.line.me/v2/bot/message/push"
        )

    def is_configured(self) -> bool:
        return bool(
            self.token
            and self.user_id
        )

    def send(self, message: str) -> bool:
        if not self.is_configured():
            print(
                "LINE Alert skipped: "
                "LINE credentials are not configured"
            )
            return False

        if not message:
            return False

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        payload = {
            "to": self.user_id,
            "messages": [
                {
                    "type": "text",
                    "text": message[:5000],
                }
            ],
        }

        try:
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )

            if response.status_code == 200:
                return True

            print(
                "LINE Alert failed:",
                response.status_code,
                response.text,
            )
            return False

        except requests.RequestException as error:
            print(
                "LINE Alert connection error:",
                error,
            )
            return False

    def position_opened(
        self,
        position,
        portfolio_summary: dict,
    ) -> bool:

        message = (
            "✅ POSITION OPENED\n"
            f"Symbol: {position.symbol}\n"
            f"Side: {position.side}\n"
            f"Leverage: {position.leverage}x\n"
            f"Entry: {position.entry_price}\n"
            f"Quantity: {position.quantity}\n"
            f"Notional: {position.notional_value:.4f} USDT\n"
            f"Margin: {position.required_margin:.4f} USDT\n"
            f"Risk: {position.risk_amount:.4f} USDT\n"
            f"SL: {position.stop_loss}\n"
            f"TP: {position.take_profit}\n"
            f"Score: {position.strategy_score}\n"
            f"Margin Used: "
            f"{portfolio_summary.get('margin_used', 0):.4f} USDT\n"
            f"Open Risk: "
            f"{portfolio_summary.get('open_risk', 0):.4f} USDT\n"
            f"Equity: "
            f"{portfolio_summary.get('equity', 0):.4f} USDT"
        )

        return self.send(message)

    def position_closed(
        self,
        position,
        portfolio_summary: dict,
    ) -> bool:

        icon = (
            "🟢"
            if position.realized_pnl >= 0
            else "🔴"
        )

        message = (
            f"{icon} POSITION CLOSED\n"
            f"Symbol: {position.symbol}\n"
            f"Side: {position.side}\n"
            f"Leverage: {position.leverage}x\n"
            f"Entry: {position.entry_price}\n"
            f"Exit: {position.exit_price}\n"
            f"Reason: {position.exit_reason}\n"
            f"PnL: {position.realized_pnl:.4f} USDT\n"
            f"Fees: "
            f"{position.entry_fee + position.exit_fee:.4f} USDT\n"
            f"Holding: "
            f"{position.holding_seconds():.0f} sec\n"
            f"Equity: "
            f"{portfolio_summary.get('equity', 0):.4f} USDT\n"
            f"Win Rate: "
            f"{portfolio_summary.get('win_rate', 0):.2f}%"
        )

        return self.send(message)

    def risk_rejected(
        self,
        symbol: str,
        reason: str,
        portfolio_summary: Optional[dict] = None,
    ) -> bool:

        portfolio_summary = (
            portfolio_summary or {}
        )

        message = (
            "⚠️ TRADE REJECTED\n"
            f"Symbol: {symbol}\n"
            f"Reason: {reason}\n"
            f"Open Positions: "
            f"{portfolio_summary.get('open_positions', 0)}\n"
            f"Margin Usage: "
            f"{portfolio_summary.get('margin_usage_pct', 0) * 100:.2f}%\n"
            f"Open Risk: "
            f"{portfolio_summary.get('open_risk', 0):.4f} USDT"
        )

        return self.send(message)

    def websocket_disconnected(
        self,
        reason: str,
        reconnect_seconds: int,
    ) -> bool:

        return self.send(
            "🔌 WEBSOCKET DISCONNECTED\n"
            f"Reason: {reason}\n"
            f"Reconnect in: {reconnect_seconds} sec"
        )

    def websocket_reconnected(self) -> bool:
        return self.send(
            "✅ WEBSOCKET RECONNECTED\n"
            "Trading engine is online again."
        )

    def recovery_restored(
        self,
        recovered_positions: int,
    ) -> bool:

        return self.send(
            "♻️ POSITION RECOVERY\n"
            f"Restored open positions: "
            f"{recovered_positions}"
        )

    def system_started(self) -> bool:
        return self.send(
            "🚀 TCP Crypto AI Trader started\n"
            "Mode: PAPER LEVERAGED"
        )


def main():
    line = LineAlert()

    success = line.send(
        "✅ TCP Crypto AI Trader\n"
        "LINE Alert integration test successful."
    )

    print(
        "LINE test:",
        "PASS" if success else "FAIL",
    )


if __name__ == "__main__":
    main()