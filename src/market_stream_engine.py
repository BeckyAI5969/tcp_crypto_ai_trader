import asyncio
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
from binance import AsyncClient, BinanceSocketManager

from config.symbols import SYMBOLS
from src.candle_buffer import CandleBuffer
from src.indicator_engine import IndicatorEngine
from src.strategy_engine import StrategyEngine
from src.paper_trader import PaperTrader


class MarketStreamEngine:

    def __init__(self):
        self.timeframe = "15m"
        self.history_limit = 300

        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        self.signal_csv = self.log_dir / "signal_history.csv"
        self.replay_json = self.log_dir / "signal_replay.jsonl"
        self.forward_report = self.log_dir / "forward_test_report.json"

        self.signal_counts = {
            "BUY": 0,
            "SELL": 0,
            "WAIT": 0,
        }

        self.total_signals = 0
        self.started_at = datetime.now()

        self.buffer = CandleBuffer(maxlen=self.history_limit)
        self.paper_trader = PaperTrader()

        self.client = None
        self.bm = None

        with open("config/api_config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)

        self.api_key = cfg["testnet"]["api_key"]
        self.api_secret = cfg["testnet"]["api_secret"]

    async def connect(self):
        print("=" * 70)
        print("TCP MARKET STREAM ENGINE - PAPER TRADING COMPLETE")
        print("=" * 70)

        self.client = await AsyncClient.create(
            api_key=self.api_key,
            api_secret=self.api_secret,
            testnet=True,
        )

        self.bm = BinanceSocketManager(self.client)
        print("Connected to Binance Futures Testnet")

    async def load_history(self):
        print("Loading historical candles...")

        for symbol in SYMBOLS:
            klines = await self.client.futures_klines(
                symbol=symbol,
                interval=self.timeframe,
                limit=self.history_limit,
            )

            for k in klines:
                self.buffer.append(
                    symbol,
                    {
                        "open_time": k[0],
                        "open": k[1],
                        "high": k[2],
                        "low": k[3],
                        "close": k[4],
                        "volume": k[5],
                        "close_time": k[6],
                    },
                )

            print(symbol, "history loaded:", self.buffer.size(symbol))

        print("Historical candles ready")

    def process_signal(self, symbol):
        df = self.buffer.get_dataframe(symbol)

        if df.empty or len(df) < 250:
            print(symbol, "not enough candles:", len(df))
            return

        df = IndicatorEngine().calculate_dataframe(df)
        df = StrategyEngine().calculate_dataframe(df)

        latest = df.iloc[-1]

        signal = str(latest.get("Decision", "WAIT"))
        score = float(latest.get("StrategyScore", 0))
        price = float(latest["close"])

        record = {
            "time": datetime.now().isoformat(),
            "symbol": symbol,
            "timeframe": self.timeframe,
            "price": price,
            "signal": signal,
            "score": score,
            "ema20": float(latest.get("EMA20", 0)),
            "ema50": float(latest.get("EMA50", 0)),
            "ema200": float(latest.get("EMA200", 0)),
            "rsi14": float(latest.get("RSI14", 0)),
            "macd": float(latest.get("MACD", 0)),
            "macd_signal": float(latest.get("MACD_SIGNAL", 0)),
            "volume": float(latest.get("volume", 0)),
            "mode": "PAPER",
            "order_sent": False,
        }

        if signal in ["BUY", "SELL"]:
            paper_position = self.paper_trader.on_signal(
                symbol=symbol,
                signal=signal,
                price=price,
                score=score,
            )

            managed_position = self.paper_trader.update_market_price(
                symbol=symbol,
                price=price,
            )

            if managed_position is not None:
                paper_position = managed_position

        else:
            paper_position = self.paper_trader.update_market_price(
                symbol=symbol,
                price=price,
            )

        print("=" * 70)
        print(record["time"])
        print("Symbol :", symbol)
        print("Price  :", price)
        print("Signal :", signal)
        print("Score  :", score)
        print("Mode   : PAPER")

        if paper_position:
            print("Paper Position:")
            print(paper_position.to_dict())
        else:
            print("Paper Position: None")

        print("Order  : PAPER ONLY")
        print("=" * 70)

        self.save_signal(record)

        self.total_signals += 1

        if signal in self.signal_counts:
            self.signal_counts[signal] += 1
        else:
            self.signal_counts[signal] = 1

        self.save_forward_report()

    def save_signal(self, record):
        df = pd.DataFrame([record])

        if self.signal_csv.exists():
            df.to_csv(
                self.signal_csv,
                mode="a",
                header=False,
                index=False,
            )
        else:
            df.to_csv(
                self.signal_csv,
                index=False,
            )

        with open(self.replay_json, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def save_forward_report(self):
        report = {
            "started_at": self.started_at.isoformat(),
            "updated_at": datetime.now().isoformat(),
            "mode": "PAPER",
            "timeframe": self.timeframe,
            "total_signals": self.total_signals,
            "signal_counts": self.signal_counts,
            "paper_summary": self.paper_trader.summary(),
            "order_sent": False,
            "status": "RUNNING",
        }

        with open(self.forward_report, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)

    async def stream(self):
        streams = [
            f"{symbol.lower()}@kline_15m"
            for symbol in SYMBOLS
        ]

        socket = self.bm.futures_multiplex_socket(streams)

        print("Listening for closed 15m candles...")
        print("Press Ctrl + C to stop")

        async with socket as stream:
            while True:
                msg = await stream.recv()
                data = msg.get("data", {})

                if "k" not in data:
                    continue

                k = data["k"]

                if not k["x"]:
                    continue

                symbol = k["s"]

                self.buffer.append(
                    symbol,
                    {
                        "open_time": k["t"],
                        "open": k["o"],
                        "high": k["h"],
                        "low": k["l"],
                        "close": k["c"],
                        "volume": k["v"],
                        "close_time": k["T"],
                    },
                )

                self.process_signal(symbol)

    async def close(self):
        self.save_forward_report()

        print()
        print("FINAL PAPER SUMMARY")
        print(self.paper_trader.summary())
        print()

        if self.client:
            await self.client.close_connection()

        print("Disconnected")


async def main():
    engine = MarketStreamEngine()

    await engine.connect()
    await engine.load_history()

    try:
        await engine.stream()
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        await engine.close()


if __name__ == "__main__":
    asyncio.run(main())
