from futures_testnet_client import FuturesTestnetClient


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


def main():
    engine = OrderEngine()

    result = engine.market_buy(
        symbol="BTCUSDT",
        quantity=0.001
    )

    print(result)


if __name__ == "__main__":
    main()