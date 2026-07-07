"""
Offline smoke test. No network.
"""

from pathlib import Path
import csv
import tempfile

from src.validator import validate_file


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "BTCUSDT_15m.csv"
        fieldnames = [
            "symbol", "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote"
        ]
        rows = [
            ["BTCUSDT", 0, 100.0, 110.0, 90.0, 105.0, 10.0, 899999, 1000.0, 100, 5.0, 500.0],
            ["BTCUSDT", 900000, 105.0, 115.0, 100.0, 110.0, 12.0, 1799999, 1200.0, 120, 6.0, 600.0],
            ["BTCUSDT", 1800000, 110.0, 120.0, 108.0, 118.0, 11.0, 2699999, 1300.0, 130, 7.0, 700.0],
        ]
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(fieldnames)
            writer.writerows(rows)

        result = validate_file(path, interval="15m")
        if result.status != "PASS":
            print("Smoke test failed:", result)
            return 1

    print("Smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
