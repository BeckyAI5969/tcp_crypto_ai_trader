from src.futures_testnet_client import FuturesTestnetClient


class CancelOrdersEngine:

    def __init__(self):
        self.client = FuturesTestnetClient().client

    def cancel_all(self, symbol="BTCUSDT"):
        result = self.client.futures_cancel_all_open_orders(
            symbol=symbol
        )

        print("=" * 50)
        print("Cancel All Open Orders")
        print("=" * 50)
        print(result)
        print("=" * 50)

        return result


def main():
    engine = CancelOrdersEngine()
    engine.cancel_all("BTCUSDT")


if __name__ == "__main__":
    main()