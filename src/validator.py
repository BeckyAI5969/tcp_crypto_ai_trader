"""
Data quality validator for OHLCV CSV files.
Standard library only.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any


INTERVAL_MS = {
    "15m": 15 * 60_000,
}


@dataclass
class ValidationResult:
    symbol: str
    file: str
    interval: str
    rows: int
    expected_rows: int
    missing_candles: int
    duplicate_timestamps: int
    invalid_ohlc: int
    invalid_volume: int
    first_open_time: int | None
    last_open_time: int | None
    status: str


def read_csv(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "symbol": row["symbol"],
                "open_time": int(row["open_time"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
            })
    return rows


def validate_file(path: Path, interval: str = "15m") -> ValidationResult:
    rows = read_csv(path)
    if not rows:
        return ValidationResult("UNKNOWN", str(path), interval, 0, 0, 0, 0, 0, 0, None, None, "FAIL")

    rows = sorted(rows, key=lambda r: r["open_time"])
    symbol = str(rows[0]["symbol"])
    step = INTERVAL_MS[interval]
    times = [int(r["open_time"]) for r in rows]
    unique_times = set(times)

    duplicate_timestamps = len(times) - len(unique_times)
    first_time = times[0]
    last_time = times[-1]
    expected_rows = ((last_time - first_time) // step) + 1 if last_time >= first_time else 0
    missing_candles = max(0, expected_rows - len(unique_times))

    invalid_ohlc = 0
    invalid_volume = 0

    for r in rows:
        o, h, l, c = r["open"], r["high"], r["low"], r["close"]
        v = r["volume"]
        if not (h >= max(o, c) and l <= min(o, c) and h >= l and o > 0 and h > 0 and l > 0 and c > 0):
            invalid_ohlc += 1
        if v < 0:
            invalid_volume += 1

    status = "PASS"
    if expected_rows == 0 or missing_candles or duplicate_timestamps or invalid_ohlc or invalid_volume:
        status = "FAIL"

    return ValidationResult(
        symbol=symbol,
        file=str(path),
        interval=interval,
        rows=len(rows),
        expected_rows=expected_rows,
        missing_candles=missing_candles,
        duplicate_timestamps=duplicate_timestamps,
        invalid_ohlc=invalid_ohlc,
        invalid_volume=invalid_volume,
        first_open_time=first_time,
        last_open_time=last_time,
        status=status,
    )


def validate_many(paths: List[Path], interval: str = "15m") -> List[ValidationResult]:
    return [validate_file(path, interval=interval) for path in paths]


def write_reports(results: List[ValidationResult], output_dir: str = "reports") -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    payload = {
        "overall_status": "PASS" if all(r.status == "PASS" for r in results) else "FAIL",
        "results": [asdict(r) for r in results],
    }

    (out / "data_quality_report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Data Quality Report",
        "",
        f"Overall Status: **{payload['overall_status']}**",
        "",
        "| Symbol | Rows | Expected | Missing | Duplicates | Invalid OHLC | Invalid Volume | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in results:
        lines.append(
            f"| {r.symbol} | {r.rows} | {r.expected_rows} | {r.missing_candles} | "
            f"{r.duplicate_timestamps} | {r.invalid_ohlc} | {r.invalid_volume} | {r.status} |"
        )

    (out / "data_quality_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
