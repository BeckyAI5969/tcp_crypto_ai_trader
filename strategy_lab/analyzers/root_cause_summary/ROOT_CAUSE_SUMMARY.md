# Sprint 28 Root Cause Summary

Generated: `2026-07-13T16:02:54.409099+00:00`
Trade records: **1,099**
Strategy versions: **v0.1.0, v0.1.1**

## Methodology and limitation

Findings identify measured associations in recorded trades. They do not prove hidden market, execution, or implementation causes without additional evidence.

## Version metrics

| Version | Trades | Win Rate | Profit Factor | Net Profit | Expectancy | Max Drawdown |
|---|---:|---:|---:|---:|---:|---:|
| v0.1.0 | 581 | 29.2599% | 0.6411 | -6408.2217 | -11.0296 | -7776.0645 |
| v0.1.1 | 518 | 70.6564% | 1.2285 | 1736.4824 | 3.3523 | -668.9596 |

## Ranked observed loss concentrations

| Priority | Version | Category | Value | Trades | Losses | Net Profit | Loss Contribution | Confidence |
|---:|---|---|---|---:|---:|---:|---:|---|
| 1 | v0.1.1 | EXIT_REASON | STOP_LOSS | 152 | 152 | -7600.0000 | 100.00% | HIGH |
| 2 | v0.1.0 | EXIT_REASON | STOP_LOSS | 344 | 344 | -17459.9841 | 97.78% | HIGH |
| 3 | v0.1.0 | SYMBOL | SOLUSDT | 195 | 143 | -2638.4103 | 14.78% | HIGH |
| 4 | v0.1.0 | SYMBOL | ETHUSDT | 168 | 114 | -1436.5979 | 8.05% | HIGH |
| 5 | v0.1.0 | SYMBOL | BNBUSDT | 76 | 57 | -1100.3485 | 6.16% | HIGH |
| 6 | v0.1.0 | SYMBOL | XRPUSDT | 68 | 47 | -776.0048 | 4.35% | HIGH |
| 7 | v0.1.0 | SYMBOL | BTCUSDT | 74 | 50 | -456.8603 | 2.56% | HIGH |

## Interpretation rule

Each finding is a descriptive association from the master trade database. A finding must not be treated as proof that the named symbol or exit rule caused the loss.
