# TCP Crypto AI Trader v0.1.0 Backtest

## Installation

Copy the included `backtest` folder into the repository root.

Place the uploaded dataset here:

```text
data/market_dataset.csv
```

Expected structure:

```text
tcp_crypto_ai_trader/
├── src/
├── backtest/
│   ├── backtest_settings.py
│   └── run_backtest.py
├── data/
│   └── market_dataset.csv
└── reports/
```

## Run with one command

From the repository root:

```powershell
py -B backtest\run_backtest.py
```

## Output

The command creates:

```text
reports/backtest_v0.1.0/
├── backtest_summary.csv
├── trade_journal.csv
├── equity_curve.csv
├── benchmark_comparison.csv
└── backtest_run.json
```

## Method

- Uses the latest 365 days per symbol
- Replays 15-minute candles in chronological order
- Reproduces the original Weighted AI SignalEngine
- Applies the optimized rules for BTC, ETH, BNB, XRP and SOL
- Uses the real `src/main_pipeline.py` v0.1.0 for leverage, risk,
  position sizing, stop-loss, take-profit and paper execution
- Includes the same fee and slippage assumptions currently configured for
  forward paper testing
- Does not use `future_return_*` or `label_16` as trading inputs
- Uses a conservative stop-first rule when both SL and TP occur in one candle
