import json
from pathlib import Path

from binance.client import Client


class BinanceConnection:

    def __init__(self, config_path="config/api_config.json"):
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.client = self.create_client()

    def load_config(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def create_client(self):
        env = self.config.get("environment", "testnet")
        cfg = self.config[env]

        client = Client(
            cfg["api_key"],
            cfg["api_secret"],
            testnet=cfg.get("enabled", True),
        )

        client.FUTURES_URL = cfg["base_url"] + "/fapi"

        return client

    def test_connection(self):
        print("=" * 70)
        print("TCP BINANCE FUTURES TESTNET CONNECTION")
        print("=" * 70)

        print("1. Ping...")
        self.client.futures_ping()
        print("PASS")

        print("2. Server Time...")
        server_time = self.client.futures_time()
        print(server_time)

        print("3. Account...")
        account = self.client.futures_account()
        print("Can trade:", account.get("canTrade"))

        print("4. Balance...")
        balances = self.client.futures_account_balance()
        usdt = [b for b in balances if b.get("asset") == "USDT"]
        print("USDT Balance:", usdt)

        print("5. BTCUSDT Price...")
        ticker = self.client.futures_symbol_ticker(symbol="BTCUSDT")
        print("BTCUSDT:", ticker)

        print("=" * 70)
        print("BINANCE TESTNET CONNECTION PASSED")
        print("=" * 70)


def main():
    BinanceConnection().test_connection()


if __name__ == "__main__":
    main()