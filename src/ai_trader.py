import pandas as pd
from datetime import datetime

from src.risk_manager import RiskManager
from src.order_engine import OrderEngine
from src.stop_loss_engine import StopLossEngine
from src.take_profit_engine import TakeProfitEngine
from src.position_engine import PositionEngine
from src.cancel_orders_engine import CancelOrdersEngine
from src.line_alert import LineAlert


class AITrader:

    def __init__(self, symbol="BTCUSDT"):
        self.symbol = symbol
        self.csv_path = f"data/{symbol}/15m/{symbol}_15m.csv"
        self.balance = 5000
        self.risk_percent = 1
        self.min_score = 80

    def run(self):
        df = pd.read_csv(self.csv_path)
        latest = df.iloc[-1]

        price = float(latest["close"])
        signal = str(latest.get("Signal", "WAIT"))
        score = float(latest.get("AI_SCORE", 0))

        print("=" * 60)
        print("TCP Crypto AI Trader")
        print("=" * 60)
        print("Time   :", datetime.now())
        print("Symbol :", self.symbol)
        print("Price  :", price)
        print("Signal :", signal)
        print("Score  :", score)
        print("=" * 60)

        if signal not in ["BUY", "SELL"]:
            print("No trade. Signal is WAIT.")
            return

        if score < self.min_score:
            print("No trade. AI score below minimum.")
            return

        PositionEngine().get_position(self.symbol)
        CancelOrdersEngine().cancel_all(self.symbol)

        if signal == "BUY":
            stop_loss = round(price * 0.99, 2)
            take_profit = round(price * 1.02, 2)
            order_side = "BUY"
            exit_side = "SELL"
        else:
            stop_loss = round(price * 1.01, 2)
            take_profit = round(price * 0.98, 2)
            order_side = "SELL"
            exit_side = "BUY"

        risk = RiskManager(balance=self.balance, risk_percent=self.risk_percent)

        quantity = risk.calculate_position_size(
            entry_price=price,
            stop_loss=stop_loss,
            step_size=0.001
        )

        print("Stop Loss   :", stop_loss)
        print("Take Profit :", take_profit)
        print("Quantity    :", quantity)

        order_engine = OrderEngine()

        if order_side == "BUY":
            order = order_engine.market_buy(self.symbol, quantity)
        else:
            order = order_engine.market_sell(self.symbol, quantity)

        print("Main Order:")
        print(order)

        sl_order = StopLossEngine().place_stop_loss(
            symbol=self.symbol,
            side=exit_side,
            quantity=quantity,
            stop_price=stop_loss
        )

        print("Stop Loss Order:")
        print(sl_order)

        tp_order = TakeProfitEngine().place_take_profit(
            symbol=self.symbol,
            side=exit_side,
            quantity=quantity,
            take_profit_price=take_profit
        )

        print("Take Profit Order:")
        print(tp_order)

        message = f"""
🤖 TCP Crypto AI Trader

DEMO Order Executed

Symbol: {self.symbol}
Signal: {signal}
AI Score: {score}

Entry: {price}
Qty: {quantity}

SL: {stop_loss}
TP: {take_profit}
"""

        LineAlert().send(message)


def main():
    trader = AITrader()
    trader.run()


if __name__ == "__main__":
    main()