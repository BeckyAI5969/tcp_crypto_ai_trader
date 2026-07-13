"""Settings for the one-command TCP Crypto AI Trader v0.1.0 backtest."""

INITIAL_BALANCE = 5000.0
RISK_PER_TRADE = 0.01
TIMEFRAME = "15m"
LOOKBACK_DAYS = 365

# Match the current paper-forward assumptions in leverage_config.py.
TAKER_FEE_RATE = 0.0005
SLIPPAGE_RATE = 0.0003

# Conservative rule when both SL and TP are touched inside one candle.
INTRABAR_PRIORITY = "STOP_FIRST"

SYMBOL_RULES = {
    "BNBUSDT": {
        "min_score": 60,
        "rsi_low": 30,
        "rsi_high": 55,
        "atr_mode": "sma20",
        "volume_multiplier": 1.15,
        "ema_confirm": True,
        "exit_mode": "ema20_exit",
    },
    "XRPUSDT": {
        "min_score": 60,
        "rsi_low": 30,
        "rsi_high": 55,
        "atr_mode": "sma20",
        "volume_multiplier": 1.15,
        "ema_confirm": True,
        "exit_mode": "ema20_exit",
    },
    "ETHUSDT": {
        "min_score": 60,
        "rsi_low": 30,
        "rsi_high": 60,
        "atr_mode": "sma20",
        "volume_multiplier": 1.10,
        "ema_confirm": True,
        "exit_mode": "ema20_exit",
    },
    "BTCUSDT": {
        "min_score": 60,
        "rsi_low": 30,
        "rsi_high": 55,
        "atr_mode": "percentile40",
        "volume_multiplier": 1.15,
        "ema_confirm": True,
        "exit_mode": "ema20_exit",
    },
    "SOLUSDT": {
        "min_score": 60,
        "rsi_low": 30,
        "rsi_high": 60,
        "atr_mode": "percentile40",
        "volume_multiplier": 1.20,
        "ema_confirm": True,
        "exit_mode": "ema20_exit",
    },
}

BENCHMARK = {
    "BNBUSDT": {"trades": 66, "wins": 54, "losses": 12, "win_rate": 81.82,
                "gross_profit": 1214.82, "gross_loss": -652.47,
                "net_profit": 562.35, "profit_factor": 1.8619,
                "max_drawdown": -127.19, "expectancy": 8.52},
    "XRPUSDT": {"trades": 58, "wins": 46, "losses": 12, "win_rate": 79.31,
                "gross_profit": 1098.47, "gross_loss": -684.02,
                "net_profit": 414.45, "profit_factor": 1.6059,
                "max_drawdown": -260.06, "expectancy": 7.15},
    "ETHUSDT": {"trades": 121, "wins": 92, "losses": 29, "win_rate": 76.03,
                "gross_profit": 2595.75, "gross_loss": -1684.98,
                "net_profit": 910.77, "profit_factor": 1.5405,
                "max_drawdown": -365.91, "expectancy": 7.53},
    "BTCUSDT": {"trades": 62, "wins": 50, "losses": 12, "win_rate": 80.65,
                "gross_profit": 833.27, "gross_loss": -692.80,
                "net_profit": 140.47, "profit_factor": 1.2028,
                "max_drawdown": -256.26, "expectancy": 2.27},
    "SOLUSDT": {"trades": 146, "wins": 100, "losses": 46, "win_rate": 68.49,
                "gross_profit": 3022.23, "gross_loss": -2593.65,
                "net_profit": 428.58, "profit_factor": 1.1652,
                "max_drawdown": -433.81, "expectancy": 2.94},
}
