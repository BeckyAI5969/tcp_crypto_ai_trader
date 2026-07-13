"""One-command builder for Sprint 28 Module 28.1.

Run from the project root on Windows:

    py -B strategy_lab\\database\\database_builder.py
"""

from __future__ import annotations

import logging
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parents[1]

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from master_trade_database import build_master_trade_history


def configure_logging() -> None:
    """Configure deterministic console logging for one-command execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def main() -> None:
    configure_logging()
    print("=" * 72)
    print("TCP STRATEGY LAB — MODULE 28.1 MASTER TRADE DATABASE")
    print("=" * 72)

    _, report = build_master_trade_history(PROJECT_ROOT)

    print(f"Sources discovered : {report['sources_discovered']}")
    print(f"Sources loaded     : {report['sources_loaded']}")
    print(f"Master rows        : {report['master_rows']}")
    print(f"Versions           : {', '.join(report['versions']) or 'None'}")
    print(f"Symbols            : {', '.join(report['symbols']) or 'None'}")
    print(
        "Validation         : "
        + ("PASS" if report["validation"]["passed"] else "FAIL")
    )
    print("")
    print(f"Created: {report['output_file']}")
    print(
        "Validation report: "
        + str(
            Path(report["output_file"]).with_name(
                "master_trade_validation.json"
            )
        )
    )

    if not report["validation"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
