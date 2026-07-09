from pathlib import Path
import pandas as pd


class DataValidator:

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_csv(self, csv_file):
        csv_file = Path(csv_file)

        if not csv_file.exists():
            self.errors.append(f"{csv_file} not found")
            return False

        df = pd.read_csv(csv_file)

        required = [
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        for c in required:
            if c not in df.columns:
                self.errors.append(f"Missing column : {c}")

        if df.empty:
            self.errors.append("Empty dataframe")

        return df

    def validate_duplicate(self, df):
        if "open_time" not in df.columns:
            return

        dup = df.duplicated("open_time").sum()

        if dup > 0:
            self.errors.append(f"Duplicate candle : {dup}")

    def validate_missing(self, df):
        required = [
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        existing = [
            c for c in required
            if c in df.columns
        ]

        missing = df[existing].isna().sum().sum()

        if missing > 0:
            self.errors.append(
                f"Missing OHLCV values : {missing}"
            )

        ignored = df.isna().sum().sum() - missing

        if ignored > 0:
            self.warnings.append(
                f"Ignored indicator warm-up NaN values : {ignored}"
            )

    def validate_ohlc(self, df):
        if df.empty:
            return

        for c in ["open", "high", "low", "close"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        bad = df[
            (df["high"] < df["low"])
        ]

        if len(bad):
            self.errors.append(f"Invalid OHLC : {len(bad)}")

    def validate_sort(self, df):
        if "open_time" not in df.columns:
            return

        if not df["open_time"].is_monotonic_increasing:
            self.errors.append("Timestamp not ascending")

    def validate(self, csv_file):
        self.errors = []
        self.warnings = []

        df = self.validate_csv(csv_file)

        if isinstance(df, bool):
            return False

        self.validate_duplicate(df)
        self.validate_missing(df)
        self.validate_ohlc(df)
        self.validate_sort(df)

        return len(self.errors) == 0

    def report(self):
        return {
            "pass": len(self.errors) == 0,
            "errors": self.errors,
            "warnings": self.warnings,
        }