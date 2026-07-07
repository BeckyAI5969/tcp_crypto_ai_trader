from futures_testnet_client import FuturesTestnetClient

from risk_manager import RiskManager
class OrderEngine:

    def __init__(self):
        self.client = FuturesTestnetClient().client

    def market_buy(self, symbol, quantity):
        result = self.client.futures_create_order(
            symbol=symbol,
            side="BUY",
            type="MARKET",
            quantity=quantity
        )
        return result

    def market_sell(self, symbol, quantity):
        result = self.client.futures_create_order(
            symbol=symbol,
            side="SELL",
            type="MARKET",
            quantity=quantity
        )
        return result


from risk_manager import RiskManager


def main():

    entry_price = 64000
    stop_loss = 63500

    risk = RiskManager(
        balance=5000,
        risk_percent=1
    )

    qty = risk.calculate_position_size(
        entry_price=entry_price,
        stop_loss=stop_loss
    )

    print("=" * 50)
    print("Calculated Quantity :", qty)
    print("=" * 50)

    engine = OrderEngine()

    result = engine.market_buy(
        symbol="BTCUSDT",
        quantity=qty
    )

    print(result)


if __name__ == "__main__":
    main()