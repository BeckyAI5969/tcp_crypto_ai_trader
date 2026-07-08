from pathlib import Path

SRC = Path("src")

REPLACES = {
    "from risk_manager import": "from src.risk_manager import",
    "from futures_testnet_client import": "from src.futures_testnet_client import",
    "from order_engine import": "from src.order_engine import",
    "from position_engine import": "from src.position_engine import",
    "from stop_loss_engine import": "from src.stop_loss_engine import",
    "from take_profit_engine import": "from src.take_profit_engine import",
    "from cancel_orders_engine import": "from src.cancel_orders_engine import",
    "from line_alert import": "from src.line_alert import",
    "from binance_rest_engine import": "from src.binance_rest_engine import",
    "from indicator_engine import": "from src.indicator_engine import",
    "from signal_engine import": "from src.signal_engine import",
    "from ai_trader import": "from src.ai_trader import",
    "from trade_logger import": "from src.trade_logger import",
    "from performance_engine import": "from src.performance_engine import",
    "from optimizer_engine import": "from src.optimizer_engine import",
    "from explain_engine import": "from src.explain_engine import",
}

for file in SRC.glob("*.py"):
    text = file.read_text(encoding="utf-8")
    old = text

    for find, replace in REPLACES.items():
        text = text.replace(find, replace)

    if text != old:
        file.write_text(text, encoding="utf-8")
        print("Fixed:", file)

print("Package migration complete.")