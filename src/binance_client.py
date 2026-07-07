"""
TCP Crypto AI Trader
Sprint 2
Binance Data Client
"""

from binance.client import Client


class BinanceDataClient:
    """Client สำหรับดึงข้อมูลจาก Binance"""

    def __init__(self):
        self.client = Client()

    def get_latest_price(self, symbol: str) -> float:
        """ดึงราคาปัจจุบัน"""

        ticker = self.client.get_symbol_ticker(symbol=symbol)
        return float(ticker["price"])


def main():

    client = BinanceDataClient()

    symbols = [
        "BTCUSDT",
        "ETHUSDT",
        "SOLUSDT",
    ]

    print("=" * 40)
    print("TCP Crypto AI Trader")
    print("Latest Market Prices")
    print("=" * 40)

    for symbol in symbols:
        price = client.get_latest_price(symbol)
        print(f"{symbol:10} : {price}")

    print("=" * 40)


if __name__ == "__main__":
    main()