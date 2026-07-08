from src.futures_testnet_client import FuturesTestnetClient


class StopLossEngine:

    def __init__(self):
        self.client = FuturesTestnetClient().client

    def place_stop_loss(self, symbol, side, quantity, stop_price):
        result = self.client.futures_create_order(
            symbol=symbol,
            side=side,
            type="STOP_MARKET",
            stopPrice=stop_price,
            quantity=quantity,
            reduceOnly=True,
            workingType="CONTRACT_PRICE"
        )

        return result


def main():
    engine = StopLossEngine()

    result = engine.place_stop_loss(
        symbol="BTCUSDT",
        side="SELL",
        quantity=0.001,
        stop_price=62000
    )

    print(result)


if __name__ == "__main__":
    main()