import pandas as pd
from datetime import datetime

from risk_manager import RiskManager
from order_engine import OrderEngine
from stop_loss_engine import StopLossEngine
from take_profit_engine import TakeProfitEngine
from position_engine import PositionEngine
from line_alert import LineAlert


class TradingPipeline:

    def __init__(self):
        self.csv_path = "data/BTCUSDT/15m/BTCUSDT_15m.csv"
        self.symbol = "BTCUSDT"
        self.balance = 5000
        self.risk_percent = 1

    def run(self):
        df = pd.read_csv(self.csv_path)
        latest = df.iloc[-1]

        price = float(latest.get("close", 0))
        decision = str(latest.get("AI_DECISION", "WAIT"))
        score = float(latest.get("AI_SCORE", 0))

        print("=" * 60)
        print("TCP Crypto AI Trading Pipeline")
        print("=" * 60)
        print("Time     :", datetime.now())
        print("Symbol   :", self.symbol)
        print("Price    :", price)
        print("Decision :", decision)
        print("AI Score :", score)
        print("=" * 60)

        if decision not in ["BUY", "SELL"]:
            print("No trade. Decision is WAIT.")
            return

        if score < 70:
            print("No trade. AI Score below 70.")
            return

        if decision == "BUY":
            stop_loss = round(price * 0.99, 2)
            take_profit = round(price * 1.02, 2)
            order_side = "BUY"
            exit_side = "SELL"
        else:
            stop_loss = round(price * 1.01, 2)
            take_profit = round(price * 0.98, 2)
            order_side = "SELL"
            exit_side = "BUY"

        risk = RiskManager(
            balance=self.balance,
            risk_percent=self.risk_percent
        )

        quantity = risk.calculate_position_size(
            entry_price=price,
            stop_loss=stop_loss
        )

        print("Stop Loss   :", stop_loss)
        print("Take Profit :", take_profit)
        print("Quantity    :", quantity)
        print("=" * 60)

        order_engine = OrderEngine()

        if order_side == "BUY":
            order = order_engine.market_buy(self.symbol, quantity)
        else:
            order = order_engine.market_sell(self.symbol, quantity)

        print("Main Order:")
        print(order)

        sl_engine = StopLossEngine()
        sl_order = sl_engine.place_stop_loss(
            symbol=self.symbol,
            side=exit_side,
            quantity=quantity,
            stop_price=stop_loss
        )

        print("Stop Loss Order:")
        print(sl_order)

        tp_engine = TakeProfitEngine()
        tp_order = tp_engine.place_take_profit(
            symbol=self.symbol,
            side=exit_side,
            quantity=quantity,
            take_profit_price=take_profit
        )

        print("Take Profit Order:")
        print(tp_order)

        PositionEngine().get_position(self.symbol)

        message = f"""
🚀 TCP Crypto AI Trader

Order Sent on DEMO

Symbol: {self.symbol}
Decision: {decision}
AI Score: {score}

Entry Price: {price}
Quantity: {quantity}

Stop Loss: {stop_loss}
Take Profit: {take_profit}
"""

        LineAlert().send(message)


def main():
    pipeline = TradingPipeline()
    pipeline.run()


if __name__ == "__main__":
    main()