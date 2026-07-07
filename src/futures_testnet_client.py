import os
from dotenv import load_dotenv
from binance.client import Client


class FuturesTestnetClient:

    def __init__(self):
        load_dotenv()

        api_key = os.getenv("BINANCE_TESTNET_API_KEY")
        secret_key = os.getenv("BINANCE_TESTNET_SECRET_KEY")

        self.client = Client(api_key, secret_key)
        self.client.FUTURES_URL = "https://demo-fapi.binance.com/fapi"

    def get_account_balance(self):
        balances = self.client.futures_account_balance()

        print("=" * 50)
        print("Binance Futures Testnet Balance")
        print("=" * 50)

        for item in balances:
            if item["asset"] == "USDT":
                print("Asset   :", item["asset"])
                print("Balance :", item["balance"])
                print("=" * 50)
                return item

        print("USDT balance not found")
        return None


def main():
    client = FuturesTestnetClient()
    client.get_account_balance()


if __name__ == "__main__":
    main()