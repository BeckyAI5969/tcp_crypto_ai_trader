
# TCP Strategy Lab — Module 28.1

## Purpose

Combine every strategy version's `trade_journal.csv` into one validated file:

```text
strategy_lab/history/master_trade_history.csv
```

A validation report is also created:

```text
strategy_lab/history/master_trade_validation.json
```

## Installation

Extract this ZIP into the root of:

```text
tcp_crypto_ai_trader/
```

The module will be installed at:

```text
strategy_lab/database/
```

## One-command run

Open PowerShell in the project root and run:

```powershell
py -B strategy_lab\database\database_builder.py
```

## Automatic journal discovery

The builder searches:

```text
reports/**/trade_journal.csv
strategy_lab/strategies/**/trade_journal.csv
strategy_lab/strategies/**/reports/trade_journal.csv
research/**/trade_journal.csv
```

This supports the existing paths for v0.1.0, v0.1.1 and future versions.

## Validation

Run independently with:

```powershell
py -B strategy_lab\database\validate_database.py
```

The builder checks:

- Required trade fields
- Invalid timestamps
- Exit time earlier than entry time
- Duplicate trades
- Missing critical values
- Version and symbol coverage

## Tests

```powershell
py -B -m unittest tests\test_database.py -v
```

## Rollback

Delete only:

```text
strategy_lab/database/
strategy_lab/history/master_trade_history.csv
strategy_lab/history/master_trade_validation.json
```

The original trade journals are never modified.
