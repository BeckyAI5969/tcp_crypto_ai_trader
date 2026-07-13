
"""Validate an existing master trade database."""

from __future__ import annotations

from pathlib import Path
import json
import sys

import pandas as pd

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[1]

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from master_trade_database import validate_master_frame


def main() -> None:
    path = (
        PROJECT_ROOT
        / "strategy_lab"
        / "history"
        / "master_trade_history.csv"
    )
    if not path.exists():
        raise FileNotFoundError(
            f"Master database not found: {path}"
        )

    frame = pd.read_csv(path)
    result = validate_master_frame(frame)
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
