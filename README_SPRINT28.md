# TCP Crypto AI Trader — Sprint 28

Sprint 28 extends the approved Sprint 27 Strategy Lab architecture without redesigning the project.

## Modules

- **28.1 Master Trade Database** — consolidates validated trade journals into a deterministic master history.
- **28.2 Strategy Dashboard** — generates static HTML and JSON performance views from the master history and strategy manifests.
- **28.3 Root Cause Summary** — produces descriptive loss-concentration findings without claiming unproven causality.
- **28.4 Strategy Manifest** — validates and consolidates strategy metadata and parent relationships.

## One-command execution

From the repository root:

```powershell
py -B strategy_lab\run_sprint28.py
```

Linux/macOS:

```bash
python -B strategy_lab/run_sprint28.py
```

The command executes Modules 28.1 through 28.4 in dependency order and writes:

```text
strategy_lab/sprint28_validation.json
```

A non-zero exit code means the Sprint 28 pipeline failed.

## Individual module commands

```powershell
py -B strategy_lab\database\database_builder.py
py -B strategy_lab\dashboard\strategy_dashboard.py
py -B strategy_lab\analyzers\root_cause_summary.py
py -B strategy_lab\manifest\strategy_manifest.py
```

## Validation commands

```powershell
py -m compileall -q strategy_lab tests
py -m unittest discover -s tests -p "test_*.py"
```

## Generated outputs

- `strategy_lab/history/master_trade_history.csv`
- `strategy_lab/history/master_trade_validation.json`
- `strategy_lab/dashboard/strategy_dashboard.html`
- `strategy_lab/dashboard/strategy_dashboard.json`
- `strategy_lab/analyzers/root_cause_summary/ROOT_CAUSE_SUMMARY.md`
- `strategy_lab/analyzers/root_cause_summary/root_cause_summary.json`
- `strategy_lab/analyzers/root_cause_summary/root_cause_findings.csv`
- `strategy_lab/manifest/strategy_manifest.json`
- `strategy_lab/manifest/strategy_manifest_validation.json`
- `strategy_lab/sprint28_validation.json`

## Research integrity

The Root Cause Summary reports observed associations and loss concentrations only. It does not prove causality. Strategy changes must still pass replay backtesting, walk-forward validation, and the approved project gates before paper or live trading.
