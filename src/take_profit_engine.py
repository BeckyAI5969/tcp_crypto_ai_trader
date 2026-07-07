from futures_testnet_client import FuturesTestnetClient


class TakeProfitEngine:

    def __init__(self):
        self.client = FuturesTestnetClient().client

    def place_take_profit(self, symbol, side, quantity, take_profit_price):
        result = self.client.futures_create_order(
            symbol=symbol,
            side=side,
            type="TAKE_PROFIT_MARKET",
            stopPrice=take_profit_price,
            quantity=quantity,
            reduceOnly=True,
            workingType="CONTRACT_PRICE"
        )

        return result


def main():
    engine = TakeProfitEngine()

    result = engine.place_take_profit(
        symbol="BTCUSDT",
        side="SELL",
        quantity=0.001,
        take_profit_price=65000
    )

    print(result)


if __name__ == "__main__":
    main()