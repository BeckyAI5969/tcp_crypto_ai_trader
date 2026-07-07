from futures_testnet_client import FuturesTestnetClient


class PositionEngine:

    def __init__(self):
        self.client = FuturesTestnetClient().client

    def get_position(self, symbol="BTCUSDT"):
        from pprint import pprint

        positions = self.client.futures_position_information(symbol=symbol)
        print(positions)

        print("=" * 50)
        print("Current Futures Demo Position")
        print("=" * 50)

        for position in positions:
            qty = float(position["positionAmt"])

            if qty != 0:
                side = "LONG" if qty > 0 else "SHORT"

                print("Symbol       :", position["symbol"])
                print("Side         :", side)
                print("Quantity     :", position["positionAmt"])
                print("Entry Price  :", position["entryPrice"])
                print("Mark Price   :", position["markPrice"])
                print("UnrealizedPNL:", position["unRealizedProfit"])
                # print("Leverage :", position["leverage"])
                print("=" * 50)

                return position

        print("No open position")
        print("=" * 50)
        return None


def main():
    engine = PositionEngine()
    engine.get_position("BTCUSDT")


if __name__ == "__main__":
    main()