"""Simple configuration for v0.1.0 replay backtest."""

INITIAL_BALANCE = 10_000.0
RISK_PCT = 0.02
FEE_RATE = 0.0004          # 0.04% per side
SLIPPAGE_RATE = 0.0002     # 0.02% per fill
LOOKBACK_DAYS = 365
TIMEFRAME = "15m"
ONE_POSITION_PER_SYMBOL = True

# Previous optimized entry conditions retained as the signal baseline.
# Risk, leverage, position sizing, SL and TP come from v0.1.0 MainPipeline.
SYMBOL_CONFIG = {
    "BNBUSDT": {
        "min_score": 60,
        "rsi_min": 30,
        "rsi_max": 55,
        "volume_multiplier": 1.15,
        "ema_confirm": True,
    },
    "XRPUSDT": {
        "min_score": 60,
        "rsi_min": 30,
        "rsi_max": 55,
        "volume_multiplier": 1.15,
        "ema_confirm": True,
    },
    "ETHUSDT": {
        "min_score": 60,
        "rsi_min": 30,
        "rsi_max": 60,
        "volume_multiplier": 1.10,
        "ema_confirm": True,
    },
    "BTCUSDT": {
        "min_score": 60,
        "rsi_min": 30,
        "rsi_max": 55,
        "volume_multiplier": 1.15,
        "ema_confirm": True,
    },
    "SOLUSDT": {
        "min_score": 60,
        "rsi_min": 30,
        "rsi_max": 60,
        "volume_multiplier": 1.20,
        "ema_confirm": True,
    },
}

BENCHMARK = {
    "BNBUSDT": {
        "trades": 66,
        "win_rate": 81.82,
        "net_profit": 562.35,
        "profit_factor": 1.8619,
        "max_drawdown": -127.19,
        "expectancy": 8.52,
    },
    "XRPUSDT": {
        "trades": 58,
        "win_rate": 79.31,
        "net_profit": 414.45,
        "profit_factor": 1.6059,
        "max_drawdown": -260.06,
        "expectancy": 7.15,
    },
    "ETHUSDT": {
        "trades": 121,
        "win_rate": 76.03,
        "net_profit": 910.77,
        "profit_factor": 1.5405,
        "max_drawdown": -365.91,
        "expectancy": 7.53,
    },
    "BTCUSDT": {
        "trades": 62,
        "win_rate": 80.65,
        "net_profit": 140.47,
        "profit_factor": 1.2028,
        "max_drawdown": -256.26,
        "expectancy": 2.27,
    },
    "SOLUSDT": {
        "trades": 146,
        "win_rate": 68.49,
        "net_profit": 428.58,
        "profit_factor": 1.1652,
        "max_drawdown": -433.81,
        "expectancy": 2.94,
    },
}
