import ast
import importlib
import json
import os
import py_compile
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv


@dataclass
class AuditCheck:
    name: str
    status: str
    message: str


class ProductionReadinessAudit:

    REQUIRED_FILES = [
        "start.py",
        "requirements.txt",
        ".env.example",
        "src/market_stream_engine.py",
        "src/execution_engine.py",
        "src/execution_router.py",
        "src/paper_trader.py",
        "src/paper_execution.py",
        "src/paper_position.py",
        "src/paper_portfolio.py",
        "src/position_manager.py",
        "src/position_state_store.py",
        "src/risk_manager.py",
        "src/position_sizer.py",
        "src/portfolio_risk.py",
        "src/leverage_config.py",
        "src/leverage_manager.py",
        "src/margin_calculator.py",
        "src/liquidation_guard.py",
        "src/line_alert.py",
        "src/trade_journal_engine.py",
        "src/daily_report_engine.py",
        "src/reporting_engine.py",
        "src/daily_scheduler.py",
    ]

    REQUIRED_ENV_NAMES = [
        "TRADING_MODE",
        "BINANCE_TESTNET_API_KEY",
        "BINANCE_TESTNET_API_SECRET",
        "LINE_CHANNEL_ACCESS_TOKEN",
        "LINE_USER_ID",
        "APP_TIMEZONE",
        "DAILY_REPORT_HOUR",
        "DAILY_REPORT_MINUTE",
    ]

    IMPORT_TARGETS = [
        "src.leverage_config",
        "src.leverage_manager",
        "src.margin_calculator",
        "src.liquidation_guard",
        "src.position_sizer",
        "src.risk_manager",
        "src.paper_position",
        "src.paper_portfolio",
        "src.position_state_store",
        "src.paper_execution",
        "src.position_manager",
        "src.line_alert",
        "src.trade_journal_engine",
        "src.daily_report_engine",
        "src.reporting_engine",
        "src.daily_scheduler",
        "src.paper_trader",
        "src.execution_router",
        "src.execution_engine",
        "src.market_stream_engine",
        "start",
    ]

    FORBIDDEN_TRACKED_FILES = [
        ".env",
        "config/api_config.json",
        "logs/paper_state.json",
    ]

    def __init__(self, project_root: str = "."):
        self.root = Path(project_root).resolve()
        self.checks: list[AuditCheck] = []
        self.report_file = (
            self.root / "logs" / "production_readiness_audit.json"
        )
        self.report_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def run(self) -> int:
        print("=" * 78)
        print("TCP CRYPTO AI TRADER - PRODUCTION READINESS AUDIT")
        print("=" * 78)

        self._check_required_files()
        self._check_python_syntax()
        self._check_imports()
        self._check_environment_template()
        self._check_runtime_environment()
        self._check_gitignore()
        self._check_tracked_secrets()
        self._check_start_contract()
        self._check_reporting_contract()
        self._check_recovery_contract()
        self._write_report()
        self._print_summary()

        return 0 if self._is_pass() else 1

    def _add(
        self,
        name: str,
        status: str,
        message: str,
    ):
        check = AuditCheck(
            name=name,
            status=status,
            message=message,
        )
        self.checks.append(check)

        icon = {
            "PASS": "[PASS]",
            "WARN": "[WARN]",
            "FAIL": "[FAIL]",
        }.get(status, "[INFO]")

        print(f"{icon} {name}: {message}")

    def _check_required_files(self):
        missing = [
            relative
            for relative in self.REQUIRED_FILES
            if not (self.root / relative).exists()
        ]

        if missing:
            self._add(
                "Required files",
                "FAIL",
                "Missing: " + ", ".join(missing),
            )
        else:
            self._add(
                "Required files",
                "PASS",
                f"All {len(self.REQUIRED_FILES)} files found",
            )

    def _check_python_syntax(self):
        failures = []

        for file_path in self._python_files():
            try:
                py_compile.compile(
                    str(file_path),
                    doraise=True,
                )
            except Exception as error:
                failures.append(
                    f"{file_path.relative_to(self.root)}: {error}"
                )

        if failures:
            self._add(
                "Python syntax",
                "FAIL",
                " | ".join(failures[:5]),
            )
        else:
            self._add(
                "Python syntax",
                "PASS",
                "All project Python files compiled",
            )

    def _check_imports(self):
        failures = []

        sys.path.insert(0, str(self.root))

        try:
            for module_name in self.IMPORT_TARGETS:
                try:
                    importlib.import_module(module_name)
                except Exception as error:
                    failures.append(
                        f"{module_name}: "
                        f"{type(error).__name__}: {error}"
                    )
        finally:
            if sys.path and sys.path[0] == str(self.root):
                sys.path.pop(0)

        if failures:
            self._add(
                "Module imports",
                "FAIL",
                " | ".join(failures[:8]),
            )
        else:
            self._add(
                "Module imports",
                "PASS",
                f"Imported {len(self.IMPORT_TARGETS)} modules",
            )

    def _check_environment_template(self):
        template = self.root / ".env.example"

        if not template.exists():
            self._add(
                "Environment template",
                "FAIL",
                ".env.example not found",
            )
            return

        names = self._read_env_names(template)
        missing = [
            name
            for name in self.REQUIRED_ENV_NAMES
            if name not in names
        ]

        if missing:
            self._add(
                "Environment template",
                "FAIL",
                "Missing variables: " + ", ".join(missing),
            )
        else:
            self._add(
                "Environment template",
                "PASS",
                "Required environment variables are documented",
            )

    def _check_runtime_environment(self):
        env_file = self.root / ".env"

        if not env_file.exists():
            self._add(
                "Runtime environment",
                "WARN",
                ".env not found on this machine; create it on the Cloud VM",
            )
            return

        load_dotenv(env_file)

        required_runtime_names = [
            "BINANCE_TESTNET_API_KEY",
            "BINANCE_TESTNET_API_SECRET",
            "LINE_CHANNEL_ACCESS_TOKEN",
            "LINE_USER_ID",
        ]

        missing = [
            name
            for name in required_runtime_names
            if not os.getenv(name)
        ]

        if missing:
            self._add(
                "Runtime environment",
                "WARN",
                "Missing local runtime values: "
                + ", ".join(missing)
                + ". Configure them on the Cloud VM before starting.",
            )
        else:
            self._add(
                "Runtime environment",
                "PASS",
                "Required runtime secrets are present",
            )

    def _check_gitignore(self):
        gitignore = self.root / ".gitignore"

        if not gitignore.exists():
            self._add(
                ".gitignore",
                "FAIL",
                ".gitignore not found",
            )
            return

        lines = {
            line.strip()
            for line in gitignore.read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines()
            if line.strip()
            and not line.strip().startswith("#")
        }

        required_patterns = {
            ".env",
            "__pycache__/",
            "*.pyc",
            "logs/",
        }

        missing = sorted(
            pattern
            for pattern in required_patterns
            if pattern not in lines
        )

        if missing:
            self._add(
                ".gitignore",
                "FAIL",
                "Missing patterns: " + ", ".join(missing),
            )
        else:
            self._add(
                ".gitignore",
                "PASS",
                "Secrets, caches, and logs are ignored",
            )

    def _check_tracked_secrets(self):
        if not (self.root / ".git").exists():
            self._add(
                "Tracked secrets",
                "WARN",
                "Git metadata not found; skipped tracked-file check",
            )
            return

        try:
            output = subprocess.check_output(
                ["git", "ls-files"],
                cwd=self.root,
                text=True,
                stderr=subprocess.STDOUT,
            )
        except Exception as error:
            self._add(
                "Tracked secrets",
                "WARN",
                f"Unable to query Git: {error}",
            )
            return

        tracked = {
            line.strip().replace("\\", "/")
            for line in output.splitlines()
            if line.strip()
        }

        dangerous = [
            item
            for item in self.FORBIDDEN_TRACKED_FILES
            if item in tracked
        ]

        if dangerous:
            self._add(
                "Tracked secrets",
                "FAIL",
                "Sensitive files tracked: "
                + ", ".join(dangerous),
            )
        else:
            self._add(
                "Tracked secrets",
                "PASS",
                "No known sensitive runtime files are tracked",
            )

    def _check_start_contract(self):
        path = self.root / "start.py"

        if not path.exists():
            self._add(
                "Start contract",
                "FAIL",
                "start.py not found",
            )
            return

        source = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        required_tokens = [
            "MarketStreamEngine",
            "DailyScheduler",
            "run_forever",
            "shutdown",
        ]

        missing = [
            token
            for token in required_tokens
            if token not in source
        ]

        if missing:
            self._add(
                "Start contract",
                "FAIL",
                "Missing integration points: "
                + ", ".join(missing),
            )
        else:
            self._add(
                "Start contract",
                "PASS",
                "Market stream and scheduler are wired",
            )

    def _check_reporting_contract(self):
        required_methods = {
            "src/reporting_engine.py": [
                "record_position_opened",
                "record_position_closed",
                "record_risk_rejected",
                "send_daily_line",
            ],
            "src/paper_trader.py": [
                "refresh_reporting",
                "send_daily_report",
            ],
        }

        failures = []

        for relative, method_names in required_methods.items():
            path = self.root / relative

            if not path.exists():
                failures.append(f"{relative}: file missing")
                continue

            found = self._defined_method_names(path)
            missing = [
                name
                for name in method_names
                if name not in found
            ]

            if missing:
                failures.append(
                    f"{relative}: missing {', '.join(missing)}"
                )

        if failures:
            self._add(
                "Reporting integration",
                "FAIL",
                " | ".join(failures),
            )
        else:
            self._add(
                "Reporting integration",
                "PASS",
                "Journal, dashboard, and daily reporting are connected",
            )

    def _check_recovery_contract(self):
        path = self.root / "src/position_state_store.py"

        if not path.exists():
            self._add(
                "Recovery contract",
                "FAIL",
                "position_state_store.py not found",
            )
            return

        source = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        required_fields = [
            "leverage",
            "margin_mode",
            "notional_value",
            "required_margin",
            "risk_amount",
            "entry_fee",
            "exit_fee",
            "funding_fee",
        ]

        missing = [
            field
            for field in required_fields
            if field not in source
        ]

        if missing:
            self._add(
                "Recovery contract",
                "FAIL",
                "Missing restored fields: "
                + ", ".join(missing),
            )
        else:
            self._add(
                "Recovery contract",
                "PASS",
                "Leverage, margin, risk, and fees are restored",
            )

    def _python_files(self) -> Iterable[Path]:
        ignored_parts = {
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            "logs",
        }

        for file_path in self.root.rglob("*.py"):
            if any(
                part in ignored_parts
                for part in file_path.parts
            ):
                continue

            yield file_path

    @staticmethod
    def _read_env_names(path: Path) -> set[str]:
        names = set()

        for raw_line in path.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines():
            line = raw_line.strip()

            if (
                not line
                or line.startswith("#")
                or "=" not in line
            ):
                continue

            names.add(
                line.split("=", 1)[0].strip()
            )

        return names

    @staticmethod
    def _defined_method_names(path: Path) -> set[str]:
        try:
            tree = ast.parse(
                path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            )
        except SyntaxError:
            return set()

        return {
            node.name
            for node in ast.walk(tree)
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        }

    def _is_pass(self) -> bool:
        return not any(
            check.status == "FAIL"
            for check in self.checks
        )

    def _write_report(self):
        report = {
            "generated_at":
                datetime.now().isoformat(),
            "project_root":
                str(self.root),
            "overall_status":
                "PASS" if self._is_pass() else "FAIL",
            "checks": [
                asdict(check)
                for check in self.checks
            ],
        }

        temporary = self.report_file.with_suffix(
            ".json.tmp"
        )

        with open(
            temporary,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                report,
                file,
                indent=4,
                ensure_ascii=False,
            )

        temporary.replace(self.report_file)

    def _print_summary(self):
        passes = sum(
            check.status == "PASS"
            for check in self.checks
        )
        warnings = sum(
            check.status == "WARN"
            for check in self.checks
        )
        failures = sum(
            check.status == "FAIL"
            for check in self.checks
        )

        print()
        print("=" * 78)
        print(
            "PRODUCTION READINESS AUDIT:",
            "PASS" if failures == 0 else "FAIL",
        )
        print("=" * 78)
        print("PASS :", passes)
        print("WARN :", warnings)
        print("FAIL :", failures)
        print("Report:", self.report_file)


def main():
    audit = ProductionReadinessAudit()
    raise SystemExit(audit.run())


if __name__ == "__main__":
    main()