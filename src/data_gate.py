"""
Sprint 1 Data Gate.
Runs downloader and validator.
"""

from __future__ import annotations

from src.downloader import DownloadConfig, download_all
from src.validator import validate_many, write_reports


def main() -> int:
    config = DownloadConfig(
        symbols=["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        interval="15m",
        days=30,
        output_dir="data/raw",
    )
    paths = download_all(config)
    results = validate_many(paths, interval=config.interval)
    write_reports(results, output_dir="reports")

    if all(r.status == "PASS" for r in results):
        print("SPRINT 1 DATA GATE: PASS")
        return 0

    print("SPRINT 1 DATA GATE: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
