import asyncio
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
from binance import AsyncClient, BinanceSocketManager

from config.symbols import SYMBOLS
from src.candle_buffer import CandleBuffer
from src.execution_engine import ExecutionEngine
from src.indicator_engine import IndicatorEngine
from src.strategy_engine import StrategyEngine


class MarketStreamEngine:
    def __init__(self):
        self.history_limit = 300
        self.minimum_bars = 250
        self.signal_timeframe = "15m"
        self.confirmation_timeframe = "5m"
        self.entry_timeframe = "1m"

        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        self.signal_csv = self.log_dir / "signal_history.csv"
        self.replay_json = self.log_dir / "signal_replay.jsonl"
        self.execution_json = self.log_dir / "execution_events.jsonl"
        self.forward_report = self.log_dir / "forward_test_report.json"

        self.signal_counts = {"BUY": 0, "SELL": 0, "WAIT": 0}
        self.execution_counts = {}
        self.total_signals = 0
        self.total_execution_events = 0
        self.started_at = datetime.now()
        self.reconnect_count = 0
        self.last_disconnect_at = None
        self.last_disconnect_reason = None

        self.buffers = {
            self.signal_timeframe: CandleBuffer(maxlen=self.history_limit),
            self.confirmation_timeframe: CandleBuffer(maxlen=self.history_limit),
            self.entry_timeframe: CandleBuffer(maxlen=self.history_limit),
        }
        self.execution_engine = ExecutionEngine(
            execution_mode="PAPER",
            signal_validity_minutes=15,
        )

        self.client = None
        self.socket_manager = None

        with open("config/api_config.json", "r", encoding="utf-8") as file:
            config = json.load(file)

        self.api_key = config["testnet"]["api_key"]
        self.api_secret = config["testnet"]["api_secret"]

    async def _close_client_safely(self):
        if self.client is None:
            return

        try:
            await self.client.close_connection()
        except Exception:
            pass
        finally:
            self.client = None
            self.socket_manager = None

    async def connect(self):
        await self._close_client_safely()

        print("=" * 72)
        print("TCP MARKET STREAM ENGINE - SPRINT 15 FINAL INTEGRATION")
        print("=" * 72)

        self.client = await AsyncClient.create(
            api_key=self.api_key,
            api_secret=self.api_secret,
            testnet=True,
        )
        self.socket_manager = BinanceSocketManager(self.client)
        print("Connected to Binance Futures Testnet")
        print("Execution mode: PAPER")

    async def load_history(self):
        print("Loading closed historical candles...")
        now_ms = int(datetime.now().timestamp() * 1000)

        for timeframe in (
            self.signal_timeframe,
            self.confirmation_timeframe,
            self.entry_timeframe,
        ):
            buffer = self.buffers[timeframe]

            for symbol in SYMBOLS:
                klines = await self.client.futures_klines(
                    symbol=symbol,
                    interval=timeframe,
                    limit=self.history_limit,
                )

                for kline in klines:
                    close_time = int(kline[6])
                    if close_time >= now_ms:
                        continue

                    buffer.append(
                        symbol,
                        {
                            "open_time": kline[0],
                            "open": kline[1],
                            "high": kline[2],
                            "low": kline[3],
                            "close": kline[4],
                            "volume": kline[5],
                            "close_time": close_time,
                        },
                    )

                print(f"{symbol} {timeframe} history loaded: {buffer.size(symbol)}")

        print("Historical candles ready")

    def process_15m_close(self, symbol):
        df = self._calculate_indicators(
            symbol=symbol,
            timeframe=self.signal_timeframe,
            include_strategy=True,
        )
        if df is None:
            return

        latest = df.iloc[-1]
        signal = str(latest.get("Decision", "WAIT")).upper()
        score = float(latest.get("StrategyScore", 0.0))
        price = float(latest["close"])
        atr = float(latest.get("ATR14", 0.0))

        event = self.execution_engine.on_15m_signal(
            symbol=symbol,
            signal=signal,
            score=score,
            signal_price=price,
            atr=atr,
        )

        record = {
            "time": datetime.now().isoformat(),
            "symbol": symbol,
            "timeframe": self.signal_timeframe,
            "price": price,
            "signal": signal,
            "score": score,
            "signal_strength": str(latest.get("SignalStrength", "NONE")),
            "signal_reason": str(latest.get("SignalReason", "")),
            "atr14": atr,
            "ema20": float(latest.get("EMA20", 0.0)),
            "ema50": float(latest.get("EMA50", 0.0)),
            "ema200": float(latest.get("EMA200", 0.0)),
            "rsi14": float(latest.get("RSI14", 0.0)),
            "macd": float(latest.get("MACD", 0.0)),
            "macd_signal": float(latest.get("MACD_SIGNAL", 0.0)),
            "volume": float(latest.get("volume", 0.0)),
            "mode": "MTF_RISK_PAPER",
            "execution_stage": event.stage,
            "execution_action": event.action,
            "execution_message": event.message,
            "order_sent": False,
        }

        self.save_signal(record)
        self.save_execution_event(event)
        self.total_signals += 1
        self.signal_counts[signal] = self.signal_counts.get(signal, 0) + 1

        print("=" * 72)
        print(record["time"])
        print("15m SIGNAL")
        print("Symbol   :", symbol)
        print("Price    :", price)
        print("Signal   :", signal)
        print("Score    :", score)
        print("Strength :", record["signal_strength"])
        print("Action   :", event.action)
        print("Message  :", event.message)
        print("=" * 72)

        self.save_forward_report()

    def process_5m_close(self, symbol):
        df = self._calculate_indicators(
            symbol=symbol,
            timeframe=self.confirmation_timeframe,
            include_strategy=False,
        )
        if df is None:
            return

        latest = df.iloc[-1]
        event = self.execution_engine.on_5m_close(
            symbol=symbol,
            ema20=float(latest["EMA20"]),
            ema50=float(latest["EMA50"]),
            macd=float(latest["MACD"]),
            macd_signal=float(latest["MACD_SIGNAL"]),
            rsi14=float(latest["RSI14"]),
            volume=float(latest["volume"]),
            volume_ma20=float(latest["VOLUME_MA20"]),
        )
        self.save_execution_event(event)

        if event.action not in {"SKIP", "WAIT"}:
            print("=" * 72)
            print("5m CONFIRMATION")
            print("Symbol  :", symbol)
            print("Action  :", event.action)
            print("Message :", event.message)
            print("Details :", event.details)
            print("=" * 72)

        self.save_forward_report()

    def process_1m_close(self, symbol):
        df = self._calculate_indicators(
            symbol=symbol,
            timeframe=self.entry_timeframe,
            include_strategy=False,
        )
        if df is None:
            return

        latest = df.iloc[-1]
        event = self.execution_engine.on_1m_close(
            symbol=symbol,
            current_price=float(latest["close"]),
            ema20=float(latest["EMA20"]),
            ema50=float(latest["EMA50"]),
            rsi14=float(latest["RSI14"]),
            macd=float(latest["MACD"]),
            macd_signal=float(latest["MACD_SIGNAL"]),
        )
        self.save_execution_event(event)

        if event.action not in {"SKIP", "WAIT"}:
            print("=" * 72)
            print("1m ENTRY")
            print("Symbol  :", symbol)
            print("Action  :", event.action)
            print("Message :", event.message)
            print("Details :", event.details)
            print("=" * 72)

        self.execution_engine.expire_signals()
        self.execution_engine.clear_inactive_signals()
        self.save_forward_report()

    def process_tick(self, symbol, price):
        if not self.execution_engine.router.has_open_position(symbol):
            return

        event = self.execution_engine.on_tick(symbol=symbol, price=price)
        self.save_execution_event(event)

        if event.action == "CLOSE":
            print("=" * 72)
            print("POSITION CLOSED")
            print("Symbol  :", symbol)
            print("Price   :", price)
            print("Message :", event.message)
            print("Details :", event.details)
            print("=" * 72)
            self.save_forward_report()

    def append_closed_candle(self, symbol, timeframe, kline):
        buffer = self.buffers.get(timeframe)
        if buffer is None:
            return

        buffer.append(
            symbol,
            {
                "open_time": kline["t"],
                "open": kline["o"],
                "high": kline["h"],
                "low": kline["l"],
                "close": kline["c"],
                "volume": kline["v"],
                "close_time": kline["T"],
            },
        )

    def _calculate_indicators(self, symbol, timeframe, include_strategy):
        buffer = self.buffers[timeframe]
        df = buffer.get_dataframe(symbol)

        if df.empty or len(df) < self.minimum_bars:
            print(f"{symbol} {timeframe} not enough candles: {len(df)}")
            return None

        df = IndicatorEngine().calculate_dataframe(df)
        if include_strategy:
            df = StrategyEngine().calculate_dataframe(df)
        return df

    def save_signal(self, record):
        frame = pd.DataFrame([record])
        if self.signal_csv.exists():
            frame.to_csv(self.signal_csv, mode="a", header=False, index=False)
        else:
            frame.to_csv(self.signal_csv, index=False)

        with open(self.replay_json, "a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    def save_execution_event(self, event):
        record = event.to_dict()
        with open(self.execution_json, "a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

        self.total_execution_events += 1
        self.execution_counts[event.action] = self.execution_counts.get(event.action, 0) + 1

    def save_forward_report(self):
        report = {
            "started_at": self.started_at.isoformat(),
            "updated_at": datetime.now().isoformat(),
            "mode": "MTF_RISK_PAPER",
            "timeframes": {
                "signal": self.signal_timeframe,
                "confirmation": self.confirmation_timeframe,
                "entry": self.entry_timeframe,
                "position_management": "AGG_TRADE_TICK",
            },
            "connection": {
                "reconnect_count": self.reconnect_count,
                "last_disconnect_at": (
                    self.last_disconnect_at.isoformat()
                    if self.last_disconnect_at
                    else None
                ),
                "last_disconnect_reason": self.last_disconnect_reason,
            },
            "total_signals": self.total_signals,
            "signal_counts": self.signal_counts,
            "total_execution_events": self.total_execution_events,
            "execution_counts": self.execution_counts,
            "execution_summary": self.execution_engine.summary(),
            "order_sent": False,
            "status": "RUNNING",
        }

        temporary_file = self.forward_report.with_suffix(".json.tmp")
        with open(temporary_file, "w", encoding="utf-8") as file:
            json.dump(report, file, indent=4, ensure_ascii=False)
        temporary_file.replace(self.forward_report)

    async def stream_once(self):
        streams = []
        for symbol in SYMBOLS:
            symbol_lower = symbol.lower()
            streams.extend(
                [
                    f"{symbol_lower}@kline_15m",
                    f"{symbol_lower}@kline_5m",
                    f"{symbol_lower}@kline_1m",
                    f"{symbol_lower}@aggTrade",
                ]
            )

        socket = self.socket_manager.futures_multiplex_socket(streams)

        print("Listening to:")
        print("- 15m closed candles for signals")
        print("- 5m closed candles for confirmation")
        print("- 1m closed candles for entry")
        print("- aggregate trade ticks for position management")
        print("Press Ctrl + C to stop")

        async with socket as stream:
            while True:
                message = await stream.recv()
                data = message.get("data", {})
                event_type = data.get("e")

                if event_type == "aggTrade":
                    symbol = data.get("s")
                    price = data.get("p")
                    if symbol and price is not None:
                        self.process_tick(symbol=symbol, price=float(price))
                    continue

                if event_type != "kline" or "k" not in data:
                    continue

                kline = data["k"]
                symbol = kline["s"]
                timeframe = kline["i"]

                if not kline["x"]:
                    continue

                self.append_closed_candle(symbol=symbol, timeframe=timeframe, kline=kline)

                if timeframe == self.signal_timeframe:
                    self.process_15m_close(symbol)
                elif timeframe == self.confirmation_timeframe:
                    self.process_5m_close(symbol)
                elif timeframe == self.entry_timeframe:
                    self.process_1m_close(symbol)

    async def run_forever(
        self,
        initial_delay: int = 5,
        maximum_delay: int = 60,
    ):
        reconnect_delay = initial_delay
        first_connection = True

        while True:
            try:
                await self.connect()
                await self.load_history()

                if not first_connection:
                    print(
                        "WebSocket reconnected successfully. "
                        "Recovered positions remain active."
                    )

                first_connection = False
                reconnect_delay = initial_delay
                await self.stream_once()

            except asyncio.CancelledError:
                raise

            except KeyboardInterrupt:
                raise

            except Exception as error:
                self.reconnect_count += 1
                self.last_disconnect_at = datetime.now()
                self.last_disconnect_reason = (
                    f"{type(error).__name__}: {error}"
                )

                print()
                print("WebSocket disconnected:")
                print(self.last_disconnect_reason)
                print(
                    f"Reconnecting in {reconnect_delay} seconds..."
                )
                print()

                try:
                    self.execution_engine.router.paper_trader.save_state()
                except Exception:
                    pass

                try:
                    self.save_forward_report()
                except Exception:
                    pass

                await self._close_client_safely()
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(
                    reconnect_delay * 2,
                    maximum_delay,
                )

    async def close(self):
        try:
            self.execution_engine.router.paper_trader.save_state()
        except Exception:
            pass

        try:
            self.save_forward_report()
        except Exception:
            pass

        print()
        print("FINAL EXECUTION SUMMARY")
        print(self.execution_engine.summary())
        print()

        await self._close_client_safely()
        print("Disconnected")


async def main():
    engine = MarketStreamEngine()

    try:
        await engine.run_forever()
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        await engine.close()


if __name__ == "__main__":
    asyncio.run(main())