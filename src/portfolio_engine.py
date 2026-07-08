from config.symbols import SYMBOLS

from src.binance_rest_engine import BinanceRestEngine
from src.indicator_engine import IndicatorEngine
from src.signal_engine import SignalEngine
from src.position_engine import PositionEngine
from src.ai_trader import AITrader


class PortfolioEngine:

    def __init__(self):
        pass

    def run(self):
        print("=" * 60)
        print("TCP AI Portfolio Engine")
        print("=" * 60)

        for symbol in SYMBOLS:
            print("\n")
            print("=" * 60)
            print("Processing :", symbol)
            print("=" * 60)

            csv_path = f"data/{symbol}/15m/{symbol}_15m.csv"

            try:
                BinanceRestEngine(symbol=symbol).run()

                indicator = IndicatorEngine(csv_path)
                indicator.load_csv()
                indicator.calculate()
                indicator.save()

                signal = SignalEngine(csv_path)
                signal.load_csv()
                signal.generate()
                signal.save()

                position = PositionEngine().get_position(symbol)

                if position is not None:
                    print("Position exists -> Skip")
                    continue

                AITrader(symbol=symbol).run()

            except Exception as e:
                print(f"{symbol} ERROR :", e)


def main():
    PortfolioEngine().run()


if __name__ == "__main__":
    main()