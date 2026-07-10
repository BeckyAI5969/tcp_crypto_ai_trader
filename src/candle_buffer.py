from collections import deque
import pandas as pd


class CandleBuffer:

    def __init__(self, maxlen=300):
        self.maxlen = maxlen
        self.buffers = {}

    def append(self, symbol, candle):
        symbol = symbol.upper()

        if symbol not in self.buffers:
            self.buffers[symbol] = deque(maxlen=self.maxlen)

        row = {
            "open_time": candle.get("open_time"),
            "open": float(candle.get("open")),
            "high": float(candle.get("high")),
            "low": float(candle.get("low")),
            "close": float(candle.get("close")),
            "volume": float(candle.get("volume")),
            "close_time": candle.get("close_time"),
        }

        self.buffers[symbol].append(row)

    def get_dataframe(self, symbol):
        symbol = symbol.upper()

        if symbol not in self.buffers:
            return pd.DataFrame()

        return pd.DataFrame(list(self.buffers[symbol]))

    def size(self, symbol):
        symbol = symbol.upper()

        if symbol not in self.buffers:
            return 0

        return len(self.buffers[symbol])

    def is_ready(self, symbol, min_bars=250):
        return self.size(symbol) >= min_bars

    def reset(self, symbol=None):
        if symbol is None:
            self.buffers = {}
            return

        symbol = symbol.upper()

        if symbol in self.buffers:
            self.buffers[symbol].clear()