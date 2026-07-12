"""Simple Testnet position monitor."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from binance_testnet_client import BinanceTestnetClient

@dataclass(frozen=True)
class PositionSnapshot:
    positions:list[dict[str,Any]]
    count:int
    def as_dict(self):
        return {"count":self.count,"positions":self.positions}

class TestnetPositionMonitor:
    def __init__(self, client:BinanceTestnetClient|None=None):
        self.client=client or BinanceTestnetClient()
    def read(self,symbol:str|None=None,non_zero_only:bool=False)->PositionSnapshot:
        pos=self.client.positions(symbol=symbol,non_zero_only=non_zero_only)
        return PositionSnapshot(pos,len(pos))

if __name__=="__main__":
    m=TestnetPositionMonitor()
    try:
        print(m.read(non_zero_only=True).as_dict())
    except Exception as e:
        print({"ready":False,"reason":str(e)})