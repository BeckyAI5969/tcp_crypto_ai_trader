# TCP Crypto AI Trader
# Validation Specification
Version : Sprint 10.5
Status : Architecture Freeze

---

# Objective

This document defines the validation standard for TCP Crypto AI Trader.

Every Sprint after Sprint 10 must pass every validation before moving to the next Sprint.

No exception.

---

# Regression Rule

Regression Testing MUST use exactly the same conditions as the approved baseline.

Do NOT change

- Strategy
- Timeframe
- Symbols
- Historical Period
- TP
- SL
- Commission
- Slippage
- Position Size
- AI Threshold

Only source code may change.

---

# BASELINE

Timeframe

15m

Historical Data

Same dataset as Sprint 7

Symbols

BTCUSDT
ETHUSDT
SOLUSDT
XRPUSDT
BNBUSDT

Commission

0.04%

Slippage

0.02%

Capital

100000 USDT

---

# Validation Gates

Gate A

Data Integrity

Gate B

Strategy Integrity

Gate C

Portfolio Integrity

Gate D

Paper Trading Integrity

Gate E

Regression Integrity

Gate F

Report Integrity

Gate G

Regression Certificate

Every gate must PASS.

---

# Gate A

Data Integrity

PASS

✓ Symbol correct

✓ Timeframe = 15m

✓ Historical dataset = baseline

✓ No missing candle

✓ No duplicate candle

✓ Timestamp ascending

✓ OHLC valid

✓ Volume valid

FAIL

Any error above.

---

# Gate B

Strategy Integrity

PASS

✓ Same TP

✓ Same SL

✓ Same AI Threshold

✓ Same Indicator

✓ Same EMA

✓ Same RSI

✓ Same Risk Management

FAIL

Any parameter changed.

---

# Gate C

Portfolio Integrity

PASS

✓ Allocation correct

✓ Cash never negative

✓ Equity continuous

✓ Position Size valid

✓ Exposure valid

✓ Drawdown calculation valid

---

# Gate D

Paper Trading

PASS

✓ BUY executed

✓ SELL executed

✓ TP executed

✓ SL executed

✓ Position closed

✓ PnL calculated

✓ Trade Log generated

---

# Gate E

Regression

Compare with Sprint 7

PASS

Profit Factor

No more than 5% degradation

Win Rate

No more than 3% degradation

Trade Count

Difference less than 10%

Drawdown

Increase less than 10%

Expectancy

Remain positive

---

# Gate F

Reports

Required

coin_comparison_report_v4.csv

portfolio_summary.json

paper_summary.json

trade_log.csv

equity_curve.csv

validation_summary.json

Regression_Certificate.json

---

# Gate G

Regression Certificate

PASS

Software

PASS

Strategy

PASS

Portfolio

PASS

Paper Trading

PASS

Reports

PASS

Regression

PASS

Overall

PASS

Only after all PASS

Forward Test may start.

---

# Definition of Done

Every Sprint must satisfy

Coding

PASS

Backtest

PASS

Validation

PASS

Reports

PASS

Regression

PASS

Certificate

PASS

Git Commit

PASS

Git Push

PASS

Only then Sprint is completed.

---