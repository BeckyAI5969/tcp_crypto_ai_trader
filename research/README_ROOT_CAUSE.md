# Root Cause Analyzer v1.0

## Purpose

Analyze why the v0.1.0 production backtest differs from the research
benchmark, using evidence from:

- Backtest summary and trade journal
- Benchmark comparison
- Portfolio benchmark
- Optimization Labs v2–v4
- Walk-forward report
- Feature importance
- Final trade analysis

The analyzer does not modify the strategy.

## Installation

Copy `root_cause_analyzer.py` into the existing project:

```text
tcp_crypto_ai_trader/
├── reports/
│   └── backtest_v0.1.0/
├── research/
│   ├── root_cause_analyzer.py
│   ├── portfolio_backtest_report.csv
│   ├── walk_forward_report.csv
│   ├── feature_importance.csv
│   ├── final_trade_analysis.csv
│   ├── optimization_lab_v2_best.csv
│   ├── optimization_lab_v3_best.csv
│   ├── optimization_lab_v4_best.csv
│   └── optimization_lab_v4.csv
└── src/
```

## Run with one command

From the repository root:

```powershell
py -B research\root_cause_analyzer.py
```

## Output

```text
research/root_cause_report_v1.0/
├── ROOT_CAUSE_REPORT_v1.0.md
├── root_causes.csv
├── improvement_plan.csv
├── kpi_gap_analysis.csv
├── exit_reason_analysis.csv
├── symbol_exit_analysis.csv
├── walk_forward_analysis.csv
├── feature_importance_analysis.csv
├── optimization_evolution.csv
├── data_quality.csv
└── root_cause_run.json
```

## Interpretation

The report separates:

1. Confirmed implementation differences
2. Research robustness and overfitting evidence
3. Monetary-impact assumptions
4. Data limitations
5. Prioritized improvement steps

It is designed to explain the difference, not to force v0.1.0 to reproduce
an optimized benchmark.
