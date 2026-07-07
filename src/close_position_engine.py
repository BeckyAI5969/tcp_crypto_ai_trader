from futures_testnet_client import FuturesTestnetClient


class ClosePositionEngine:

    def __init__(self):
        self.client = FuturesTestnetClient().client

    def close_position(self, symbol="BTCUSDT"):

        positions = self.client.futures_position_information(symbol=symbol)

        for position in positions:

            qty = float(position["positionAmt"])

            if qty == 0:
                continue

            side = "SELL" if qty > 0 else "BUY"

            result = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type="MARKET",
                quantity=abs(qty),
                reduceOnly=True
            )

            print("=" * 50)
            print("Position Closed")
            print("=" * 50)
            print(result)
            print("=" * 50)

            return result

        print("No position to close")
        return None


def main():

    engine = ClosePositionEngine()

    engine.close_position("BTCUSDT")


if __name__ == "__main__":
    main()