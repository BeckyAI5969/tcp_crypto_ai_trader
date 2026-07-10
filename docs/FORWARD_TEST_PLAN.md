# TCP Crypto AI Trader
# FORWARD TEST PLAN

Version: v0.10.5
Status: Approved
Date: ___________________

---

# 1. Objective

Validate the AI trading system in a live market environment using Binance Futures Testnet.

This phase is intended to verify that the trading engine performs consistently under real-time market conditions before enabling any live trading.

No real funds will be used.

---

# 2. Test Environment

Exchange
- Binance Futures Testnet

Trading Mode
- Paper Trading

Capital
- 100,000 USDT (Virtual)

Leverage
- Same as Regression Backtest

Market
- Futures

---

# 3. Locked Configuration

These parameters MUST NOT be changed during the Forward Test.

Timeframe
- 15 Minutes

Trading Symbols

- BTCUSDT
- ETHUSDT
- SOLUSDT
- XRPUSDT
- BNBUSDT

Strategy
- Current Production Strategy

Indicators
- Locked

Risk Management
- Locked

Commission
- Same as Regression

Slippage
- Same as Regression

Position Sizing
- Same as Regression

---

# 4. Test Duration

Minimum

2 Days

Target

7 Days

The test may end early if any Critical Failure occurs.

---

# 5. Daily Validation

Every trading day the following reports must be generated.

Daily Trade Log

Daily Portfolio Summary

Daily Equity Curve

Daily Performance Report

System Log

Validation Report

---

# 6. Acceptance Criteria

System Stability

PASS

No Python Exception

PASS

No Missing Orders

PASS

No Duplicate Orders

PASS

No Position Mismatch

PASS

No Data Corruption

PASS

Report Generation

PASS

Validation Score

100%

---

# 7. Trading Performance KPI

Minimum Trades

20

Win Rate

>= Baseline

Profit Factor

>= Baseline

Maximum Drawdown

<= Baseline

Risk Limit

Within Configuration

---

# 8. Critical Stop Conditions

Forward Test must stop immediately if any of the following occurs.

- Application Crash
- Incorrect Position Size
- Duplicate Orders
- Missing Exit Order
- Portfolio Calculation Error
- Data Feed Failure
- Validation Failure
- Drawdown exceeds configured limit

---

# 9. Completion Criteria

Forward Test will be considered successful when:

- Validation Score remains 100%
- No Critical Errors occur
- KPI requirements are satisfied
- Reports are complete
- Daily operation is stable

---

# 10. Deliverables

The following files must exist at the end of the test.

paper_trade_log.csv

paper_summary.json

portfolio_summary.json

equity_curve.csv

daily_reports/

validation_summary.json

Regression_Certificate.json

Forward_Test_Report.md

---

# Final Approval

Regression Backtest

PASS

Forward Test

PASS

Approved for Sprint 11

YES / NO

Approved by

_________________________

Date

_________________________