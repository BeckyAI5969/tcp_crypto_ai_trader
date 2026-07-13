# TCP Crypto AI Trader — Root Cause Report v1.0

Generated: 2026-07-12T18:59:33.898483+00:00

## Executive conclusion

The first v0.1.0 backtest is operational, but it is **not a like-for-like reproduction** of the research benchmark. The largest confirmed cause is the exit-model mismatch: the benchmark uses fixed 4% TP / -2% SL with EMA20 exit, while v0.1.0 applies ATR-based exits and dynamic risk sizing. In addition, every available walk-forward test failed, showing that the optimized benchmark itself does not generalize reliably. Therefore, the current loss must not be attributed to one coding defect or used to tune the strategy blindly.

Combined benchmark net profit: **2,456.62**  
Combined v0.1.0 net profit: **-6,408.22**

## Ranked root causes

### 1. Exit model parity (CRITICAL, confidence HIGH)

**Cause:** The benchmark and v0.1.0 backtest do not use the same exit model.

**Evidence:** Research benchmark records fixed TP=0.04 and SL=-0.02, exit_mode=ema20_exit; the v0.1.0 run records 'v0.1.0 ATR SL/TP plus profitable EMA20 exit'. STOP_LOSS produced 344 of 581 exits (59.2%) and net -17,459.98, while TAKE_PROFIT netted 10,638.70.

**Impact:** This directly changes win rate, profit factor, holding period, trade sequence, drawdown and net profit.

**Recommended improvement:** Add a benchmark-parity test mode using the exact research exit rules (4% TP, -2% SL and the original EMA20 exit implementation). Keep the current ATR exit as a separate production mode.

### 2. Research robustness / overfitting (CRITICAL, confidence HIGH)

**Cause:** The optimized benchmark is not confirmed by walk-forward testing.

**Evidence:** 5 of 5 walk-forward rows failed. Average train PF=1.0899, average test PF=0.8566.

**Impact:** The optimized benchmark can materially overstate performance on unseen periods. A production replay can therefore be worse even when its code is correct.

**Recommended improvement:** Use walk-forward and out-of-sample results as the primary go/no-go gate. Do not tune production code merely to recover the optimized in-sample benchmark.

### 3. Entry/filter/timing parity (HIGH, confidence HIGH)

**Cause:** The production replay does not generate the same trade population as the benchmark.

**Evidence:** Trade counts differ for 5 symbols, with a total absolute difference of 128 trades. This cannot be caused by position sizing alone.

**Impact:** Different entries lead to different market regimes, exits and winner/loss distributions; KPI comparison is no longer like-for-like.

**Recommended improvement:** Create a parity diagnostic that exports every accepted signal (symbol, candle time, score and each filter result). Compare it with the original research signal list before changing strategy rules.

### 4. Position sizing and cost assumptions (HIGH, confidence HIGH)

**Cause:** Production v0.1.0 uses dynamic risk-based sizing, leverage, fees and slippage; the benchmark P&L model is not documented as identical.

**Evidence:** v0.1.0 metadata: risk_per_trade=0.01, fee_per_side=0.0005, slippage_per_fill=0.0003. The research benchmark provides TP/SL and KPI values but no equivalent dynamic sizing audit trail.

**Impact:** This changes net profit and drawdown magnitude. It does not fully explain the win-rate collapse, but it amplifies monetary differences.

**Recommended improvement:** Report results both in R-multiples/percent returns and currency. For parity testing, use the same fixed notional or exact sizing function as the original research.

### 5. Execution timing assumptions (MEDIUM, confidence HIGH)

**Cause:** Entry and intrabar sequencing assumptions may differ from research.

**Evidence:** v0.1.0 uses entry_execution='current completed candle close plus slippage' and intrabar_priority='STOP_FIRST'. The benchmark report does not document the same assumptions.

**Impact:** Close-versus-next-open entry and stop-first handling can change individual outcomes, particularly volatile candles.

**Recommended improvement:** Explicitly test both signal-close and next-open execution. Retain STOP_FIRST as the conservative result when tick order is unavailable.

### 6. Trade-level traceability (MEDIUM, confidence HIGH)

**Cause:** The available research outputs are insufficient for exact trade-by-trade matching.

**Evidence:** final_trade_analysis contains 113 rows but symbol column=False, entry/exit timestamps=False.

**Impact:** The analyzer can prove KPI and model-level differences, but cannot identify the first divergent candle for every symbol.

**Recommended improvement:** Modify the original research backtest to export symbol, entry_time, exit_time, entry reason and exit reason for every trade. Then run a timestamp-level diff against trade_journal.csv.

## KPI gap by symbol

| symbol | baseline_trades | v0.1.0_trades | absolute_gap_trades | baseline_win_rate | v0.1.0_win_rate | absolute_gap_win_rate | baseline_profit_factor | v0.1.0_profit_factor | absolute_gap_profit_factor | baseline_net_profit | v0.1.0_net_profit | absolute_gap_net_profit | baseline_max_drawdown | v0.1.0_max_drawdown | absolute_gap_max_drawdown | baseline_expectancy | v0.1.0_expectancy | absolute_gap_expectancy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BNBUSDT | 66 | 76 | 10 | 81.82 | 25.0 | -56.81999999999999 | 1.8619 | 0.5719 | -1.29 | 562.35 | -1100.35 | -1662.6999999999998 | -127.19 | -1465.07 | -1337.8799999999999 | 8.52 | -14.48 | -23.0 |
| XRPUSDT | 58 | 68 | 10 | 79.31 | 30.88 | -48.43000000000001 | 1.6059 | 0.6367 | -0.9692000000000001 | 414.45 | -776.0 | -1190.45 | -260.06 | -1515.69 | -1255.63 | 7.15 | -11.41 | -18.560000000000002 |
| ETHUSDT | 121 | 168 | 47 | 76.03 | 32.14 | -43.89 | 1.5405 | 0.7239 | -0.8166 | 910.77 | -1436.6 | -2347.37 | -365.91 | -2213.58 | -1847.6699999999998 | 7.53 | -8.55 | -16.080000000000002 |
| BTCUSDT | 62 | 74 | 12 | 80.65 | 32.43 | -48.220000000000006 | 1.2028 | 0.8104 | -0.3924000000000001 | 140.47 | -456.86 | -597.33 | -256.26 | -820.0 | -563.74 | 2.27 | -6.17 | -8.44 |
| SOLUSDT | 146 | 195 | 49 | 68.49 | 26.67 | -41.81999999999999 | 1.1652 | 0.5235 | -0.6417 | 428.58 | -2638.41 | -3066.99 | -433.81 | -2641.91 | -2208.1 | 2.94 | -13.53 | -16.47 |
## Exit-reason evidence

| exit_reason | trades | wins | win_rate | gross_profit | gross_loss | net_profit | average_profit | average_holding_hours |
|---|---|---|---|---|---|---|---|---|
| EMA20_EXIT | 123 | 56 | 45.53 | 809.4119 | -396.3478 | 413.0642 | 3.3582 | 4.2358 |
| STOP_LOSS | 344 | 0 | 0.0 | 0.0 | -17459.9841 | -17459.9841 | -50.7558 | 1.6977 |
| TAKE_PROFIT | 114 | 114 | 100.0 | 10638.6982 | 0.0 | 10638.6982 | 93.3219 | 2.6535 |
## Walk-forward evidence

| symbol | passed | train_profit_factor | profit_factor | profit_factor_degradation | train_net_profit | net_profit | net_profit_degradation | train_win_rate | win_rate | win_rate_degradation | trades | max_drawdown | expectancy |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BNBUSDT | False | 1.2306 | 0.9477 | -0.2829 | 722.29 | -52.24 | -774.53 | 38.89 | 33.33 | -5.56 | 27 | -244.46 | -1.93 |
| SOLUSDT | False | 1.0413 | 0.9286 | -0.1127 | 881.33 | -487.46 | -1368.79 | 36.94 | 33.33 | -3.61 | 165 | -1261.9 | -2.95 |
| BTCUSDT | False | 1.0115 | 0.8604 | -0.1511 | 100.55 | -486.74 | -587.29 | 35.75 | 31.4 | -4.35 | 86 | -984.54 | -5.66 |
| ETHUSDT | False | 1.1508 | 0.8585 | -0.2923 | 642.2 | -210.65 | -852.85 | 37.93 | 30.77 | -7.16 | 39 | -502.46 | -5.4 |
| XRPUSDT | False | 1.0151 | 0.6878 | -0.3273 | 74.58 | -502.34 | -576.92 | 34.35 | 25.0 | -9.35 | 40 | -516.28 | -12.56 |
## Feature-importance evidence

| feature | active_rows | active_return_16 | inactive_return_16 | edge_score | buy_edge_rate |
|---|---|---|---|---|---|
| rsi_overbought | 15383 | 0.019084 | -0.023028 | 0.042113 | 26.97 |
| macd_gt_signal | 87256 | -0.00813 | -0.03056 | 0.02243 | 26.16 |
| macd_hist_positive | 87256 | -0.00813 | -0.03056 | 0.02243 | 26.16 |
| ema20_gt_ema50 | 85493 | -0.008664 | -0.029595 | 0.020931 | 25.13 |
| rsi_oversold | 16526 | -0.004038 | -0.020905 | 0.016867 | 31.52 |
| volume_gt_ma20 | 62845 | -0.010893 | -0.024063 | 0.01317 | 28.02 |
| ema50_gt_ema200 | 83881 | -0.016477 | -0.021935 | 0.005458 | 25.72 |
| price_gt_ema200 | 83291 | -0.016527 | -0.021854 | 0.005327 | 25.44 |
| rsi_neutral | 141936 | -0.025239 | 0.007109 | -0.032348 | 25.84 |
## Improvement plan

| sequence | action | reason | expected_result |
|---|---|---|---|
| 1 | Add a benchmark-parity test mode using the exact research exit rules (4% TP, -2% SL and the original EMA20 exit implementation). Keep the current ATR exit as a separate production mode. | The benchmark and v0.1.0 backtest do not use the same exit model. | Separate benchmark parity from production ATR performance. |
| 2 | Use walk-forward and out-of-sample results as the primary go/no-go gate. Do not tune production code merely to recover the optimized in-sample benchmark. | The optimized benchmark is not confirmed by walk-forward testing. | Prevent overfit benchmark from becoming a live-trading target. |
| 3 | Create a parity diagnostic that exports every accepted signal (symbol, candle time, score and each filter result). Compare it with the original research signal list before changing strategy rules. | The production replay does not generate the same trade population as the benchmark. | Explain trade-count differences with candle-level evidence. |
| 4 | Report results both in R-multiples/percent returns and currency. For parity testing, use the same fixed notional or exact sizing function as the original research. | Production v0.1.0 uses dynamic risk-based sizing, leverage, fees and slippage; the benchmark P&L model is not documented as identical. | Make monetary KPI comparison fair and auditable. |
| 5 | Explicitly test both signal-close and next-open execution. Retain STOP_FIRST as the conservative result when tick order is unavailable. | Entry and intrabar sequencing assumptions may differ from research. | Quantify execution-model sensitivity. |
| 6 | Modify the original research backtest to export symbol, entry_time, exit_time, entry reason and exit reason for every trade. Then run a timestamp-level diff against trade_journal.csv. | The available research outputs are insufficient for exact trade-by-trade matching. | Enable exact trade-by-trade root-cause attribution. |
## Decision gate

- **Do not proceed to real trading.**
- Do not optimize v0.1.0 to force agreement with the in-sample benchmark.
- First create a benchmark-parity mode and a signal audit.
- Then evaluate production v0.1.0 separately using walk-forward and out-of-sample data.
- Proceed to Testnet execution only when out-of-sample expectancy and profit factor are positive and operational checks pass.
