"""Build and validate the Strategy Lab master trade history."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import json
import logging
import os
import re
import tempfile
from typing import Iterable

import pandas as pd

from database_schema import (
    COLUMN_ALIASES,
    PREFERRED_COLUMN_ORDER,
    REQUIRED_COLUMNS,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceResult:
    """Result of loading and normalizing one trade journal."""

    strategy_version: str
    source_file: str
    rows_read: int
    rows_loaded: int
    duplicate_rows_removed: int
    missing_required_columns: list[str]
    status: str


def infer_strategy_version(path: Path) -> str:
    """Infer a strategy version from approved project path conventions."""
    text = str(path).replace("\\", "/")
    patterns = [
        r"/backtest_(v?\d+\.\d+\.\d+)/",
        r"/strategy_lab/(v?\d+\.\d+\.\d+)/",
        r"/strategies/(v?\d+\.\d+\.\d+)/",
        r"/(v?\d+\.\d+\.\d+)/reports/",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = match.group(1)
            return value if value.lower().startswith("v") else f"v{value}"

    filename_match = re.search(
        r"(v?\d+\.\d+\.\d+)",
        path.name,
        flags=re.IGNORECASE,
    )
    if filename_match:
        value = filename_match.group(1)
        return value if value.lower().startswith("v") else f"v{value}"

    return path.parent.name or "unknown"


def discover_trade_journals(project_root: Path) -> list[Path]:
    """Discover approved trade journals without scanning environment folders."""
    project_root = project_root.resolve()
    candidates: set[Path] = set()
    explicit_patterns = [
        "reports/**/trade_journal.csv",
        "strategy_lab/strategies/**/trade_journal.csv",
        "strategy_lab/strategies/**/reports/trade_journal.csv",
        "research/**/trade_journal.csv",
    ]
    for pattern in explicit_patterns:
        candidates.update(project_root.glob(pattern))

    ignored_parts = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "site-packages",
    }
    valid = [
        path.resolve()
        for path in candidates
        if path.is_file()
        and not any(part in ignored_parts for part in path.parts)
        and path.name.lower() == "trade_journal.csv"
    ]
    return sorted(set(valid), key=lambda item: str(item).lower())


def normalize_frame(
    frame: pd.DataFrame,
    strategy_version: str,
    source_file: str,
) -> tuple[pd.DataFrame, list[str]]:
    """Normalize a source journal to the master schema."""
    frame = frame.copy()
    frame.columns = [str(column).strip() for column in frame.columns]
    frame = frame.rename(
        columns={
            old: new
            for old, new in COLUMN_ALIASES.items()
            if old in frame.columns and new not in frame.columns
        }
    )

    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        return frame.iloc[0:0].copy(), missing

    frame["strategy_version"] = strategy_version
    frame["source_file"] = source_file

    for column in ("entry_time", "exit_time"):
        frame[column] = pd.to_datetime(
            frame[column],
            utc=True,
            errors="coerce",
        )

    numeric_columns = (
        "entry_price",
        "exit_price",
        "quantity",
        "notional",
        "leverage",
        "stop_loss",
        "take_profit",
        "gross_profit",
        "fees",
        "entry_fee",
        "exit_fee",
        "net_profit",
        "ai_score",
        "entry_rsi",
        "entry_atr_pct",
        "entry_volume_ratio",
        "entry_ema_gap_pct",
        "balance_after",
    )
    for column in numeric_columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["symbol"] = frame["symbol"].astype(str).str.upper().str.strip()
    if "side" in frame.columns:
        frame["side"] = frame["side"].astype(str).str.upper().str.strip()

    frame = frame.dropna(
        subset=[
            "entry_time",
            "exit_time",
            "entry_price",
            "exit_price",
            "net_profit",
        ]
    )
    frame = frame[frame["symbol"] != ""]
    frame = frame[frame["exit_time"] >= frame["entry_time"]]

    if "result" not in frame.columns:
        frame["result"] = frame["net_profit"].map(
            lambda value: "WIN" if value > 0 else "LOSS"
        )
    else:
        frame["result"] = frame["result"].astype(str).str.upper().str.strip()

    def create_trade_id(row: pd.Series) -> str:
        key = "|".join(
            [
                str(row.get("strategy_version", "")),
                str(row.get("symbol", "")),
                str(row.get("entry_time", "")),
                str(row.get("exit_time", "")),
                str(row.get("entry_price", "")),
                str(row.get("exit_price", "")),
            ]
        )
        return sha256(key.encode("utf-8")).hexdigest()[:20]

    frame["trade_id"] = frame.apply(create_trade_id, axis=1)
    return frame, []


def order_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Return columns in the stable Sprint 28 master schema order."""
    preferred = [
        column for column in PREFERRED_COLUMN_ORDER if column in frame.columns
    ]
    remaining = [column for column in frame.columns if column not in preferred]
    return frame[preferred + sorted(remaining)]


def _atomic_write_csv(frame: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        text=True,
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)
    try:
        frame.to_csv(temporary_path, index=False)
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _atomic_write_json(payload: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        text=True,
    )
    os.close(file_descriptor)
    temporary_path = Path(temporary_name)
    try:
        temporary_path.write_text(
            json.dumps(payload, indent=2, default=str),
            encoding="utf-8",
        )
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def build_master_trade_history(
    project_root: Path,
    output_path: Path | None = None,
    source_paths: Iterable[Path] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Build, validate, and atomically persist the master trade database."""
    project_root = Path(project_root).resolve()
    if not project_root.exists() or not project_root.is_dir():
        raise NotADirectoryError(f"Invalid project root: {project_root}")

    output_path = Path(output_path).resolve() if output_path else (
        project_root
        / "strategy_lab"
        / "history"
        / "master_trade_history.csv"
    )

    sources = (
        sorted(
            {Path(path).resolve() for path in source_paths},
            key=lambda item: str(item).lower(),
        )
        if source_paths is not None
        else discover_trade_journals(project_root)
    )

    source_results: list[SourceResult] = []
    loaded_frames: list[pd.DataFrame] = []

    for path in sources:
        relative_source = (
            str(path.relative_to(project_root))
            if path == project_root or project_root in path.parents
            else str(path)
        )
        version = infer_strategy_version(path)

        try:
            raw = pd.read_csv(path)
        except (OSError, UnicodeError, pd.errors.ParserError) as exc:
            LOGGER.error("Failed to read trade journal %s: %s", path, exc)
            source_results.append(
                SourceResult(
                    strategy_version=version,
                    source_file=relative_source,
                    rows_read=0,
                    rows_loaded=0,
                    duplicate_rows_removed=0,
                    missing_required_columns=[],
                    status=f"READ_ERROR: {type(exc).__name__}: {exc}",
                )
            )
            continue

        normalized, missing = normalize_frame(
            raw,
            strategy_version=version,
            source_file=relative_source,
        )
        if missing:
            LOGGER.warning(
                "Skipping trade journal %s; missing columns: %s",
                path,
                ", ".join(missing),
            )
            source_results.append(
                SourceResult(
                    strategy_version=version,
                    source_file=relative_source,
                    rows_read=len(raw),
                    rows_loaded=0,
                    duplicate_rows_removed=0,
                    missing_required_columns=missing,
                    status="SKIPPED_INVALID_SCHEMA",
                )
            )
            continue

        before = len(normalized)
        normalized = normalized.drop_duplicates(subset=["trade_id"])
        duplicates = before - len(normalized)
        loaded_frames.append(normalized)
        source_results.append(
            SourceResult(
                strategy_version=version,
                source_file=relative_source,
                rows_read=len(raw),
                rows_loaded=len(normalized),
                duplicate_rows_removed=duplicates,
                missing_required_columns=[],
                status="LOADED",
            )
        )

    if loaded_frames:
        master = pd.concat(loaded_frames, ignore_index=True, sort=False)
        before_global = len(master)
        master = master.drop_duplicates(subset=["trade_id"])
        global_duplicates = before_global - len(master)
        master = master.sort_values(
            ["strategy_version", "symbol", "entry_time", "exit_time"],
            kind="stable",
        ).reset_index(drop=True)
        master = order_columns(master)
    else:
        master = pd.DataFrame(columns=PREFERRED_COLUMN_ORDER)
        global_duplicates = 0

    validation = validate_master_frame(master)
    loaded_source_count = sum(
        result.status == "LOADED" for result in source_results
    )
    validation["source_gate_passed"] = loaded_source_count > 0
    validation["passed"] = bool(
        validation["passed"] and validation["source_gate_passed"]
    )

    report = {
        "project_root": str(project_root),
        "output_file": str(output_path),
        "sources_discovered": len(sources),
        "sources_loaded": loaded_source_count,
        "master_rows": len(master),
        "global_duplicate_rows_removed": global_duplicates,
        "versions": sorted(
            master["strategy_version"].dropna().astype(str).unique().tolist()
        ) if not master.empty else [],
        "symbols": sorted(
            master["symbol"].dropna().astype(str).unique().tolist()
        ) if not master.empty else [],
        "source_results": [asdict(result) for result in source_results],
        "validation": validation,
    }

    _atomic_write_csv(master, output_path)
    validation_path = output_path.with_name("master_trade_validation.json")
    _atomic_write_json(report, validation_path)
    LOGGER.info(
        "Master trade database built: rows=%d sources=%d validation=%s",
        len(master),
        loaded_source_count,
        validation["passed"],
    )
    return master, report


def validate_master_frame(frame: pd.DataFrame) -> dict:
    """Validate schema, uniqueness, time order, required values, and row count."""
    expected_columns = REQUIRED_COLUMNS | {
        "trade_id",
        "strategy_version",
        "source_file",
    }
    missing_columns = sorted(expected_columns - set(frame.columns))
    duplicate_trade_ids = (
        int(frame["trade_id"].duplicated().sum())
        if "trade_id" in frame.columns
        else 0
    )

    invalid_time_order = 0
    if {"entry_time", "exit_time"}.issubset(frame.columns):
        entry = pd.to_datetime(frame["entry_time"], utc=True, errors="coerce")
        exit_ = pd.to_datetime(frame["exit_time"], utc=True, errors="coerce")
        invalid_time_order = int((exit_ < entry).sum())

    null_required: dict[str, int] = {}
    for column in REQUIRED_COLUMNS:
        if column in frame.columns:
            null_required[column] = int(frame[column].isna().sum())

    row_count = len(frame)
    passed = bool(
        row_count > 0
        and not missing_columns
        and duplicate_trade_ids == 0
        and invalid_time_order == 0
        and all(value == 0 for value in null_required.values())
    )

    return {
        "passed": passed,
        "row_count": row_count,
        "missing_columns": missing_columns,
        "duplicate_trade_ids": duplicate_trade_ids,
        "invalid_time_order": invalid_time_order,
        "null_required_fields": null_required,
    }
