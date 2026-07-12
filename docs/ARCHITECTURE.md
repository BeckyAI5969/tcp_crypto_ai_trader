# TCP Crypto AI Trader Architecture

## Version
Release candidate: `v0.1.0`

## Safety Model
The default execution mode is `PAPER`. Binance Testnet connectivity and validation are supported. Live trading is disabled.

## Main Data Flow

```text
Market / Strategy Inputs
        |
        v
AI Decision Gate
        |
        v
Risk Validation
        |
        v
Dynamic Leverage
        |
        v
Stop Loss / Take Profit
        |
        v
Position Sizing
        |
        v
Trade Execution Plan
        |
        v
Order Builder
        |
        +-------------------+
        |                   |
        v                   v
Paper Execution       Testnet Validation
```

## Core Modules

- `ai_decision_engine_v2.py` — final BUY/SELL decision
- `risk_validator.py` — risk gate
- `dynamic_leverage_engine.py` — leverage selection
- `stop_loss_take_profit_engine.py` — ATR-based exit plan
- `position_size_calculator.py` — quantity and margin calculation
- `trade_execution_engine.py` — final execution approval
- `order_builder.py` — normalized order request
- `paper_execution_engine.py` — simulated execution
- `testnet_trade_executor.py` — safe Binance Testnet validation/submission gate
- `main_pipeline.py` — orchestration
- `config.py` — centralized runtime configuration
- `structured_logger.py` — JSON logging

## Runtime Modes

### PAPER
Runs the complete pipeline and creates simulated paper trades.

### TESTNET
Uses Binance Futures Testnet. Order validation is the default. Actual Testnet submission requires explicit environment configuration.

### LIVE
Not enabled in release `v0.1.0`.

## Logging

Structured logs are written under:

```text
logs/YYYY-MM-DD/
```

Categories:
- `pipeline.log`
- `trade.log`
- `risk.log`
- `error.log`

Sensitive values are redacted.

## Testing

Tests are stored under `tests/` and run with:

```powershell
py -B -m unittest discover -s tests -v
```

GitHub Actions compiles `src/` and `tests/`, then runs the test suite automatically.

## Release Gate

Release `v0.1.0` requires:

- Clean Git working tree
- Successful source compilation
- Successful unit and integration tests
- Green GitHub Actions workflow
- PAPER mode confirmed
- No `.env` file tracked by Git
- No API secrets committed
