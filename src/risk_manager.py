import pandas as pd


class RiskManager:

    def __init__(self, csv_path, account_size=10000, risk_per_trade=1.0):
        self.csv_path = csv_path
        self.account_size = account_size
        self.risk_per_trade = risk_per_trade
        self.df = None

    def load_csv(self):
        print("Loading CSV...")
        self.df = pd.read_csv(self.csv_path)

    def calculate_risk(self):
        print("Calculating risk levels...")

        latest = self.df.iloc[-1]

        close_price = latest["close"]
        atr = latest["ATR14"]
        ai_decision = latest.get("AI_DECISION", "WAIT")
        ai_score = latest.get("AI_SCORE", 0)

        risk_amount = self.account_size * (self.risk_per_trade / 100)

        if ai_decision == "BUY":
            stop_loss = close_price - (atr * 1.5)
            take_profit = close_price + (atr * 3)
            risk_per_unit = close_price - stop_loss

        elif ai_decision == "SELL":
            stop_loss = close_price + (atr * 1.5)
            take_profit = close_price - (atr * 3)
            risk_per_unit = stop_loss - close_price

        else:
            stop_loss = 0
            take_profit = 0
            risk_per_unit = 0

        position_size = 0
        if risk_per_unit > 0:
            position_size = risk_amount / risk_per_unit

        position_value = position_size * close_price

        print("=" * 45)
        print("Risk Manager")
        print("=" * 45)
        print(f"Account Size     : {self.account_size:.2f}")
        print(f"Risk Per Trade   : {self.risk_per_trade:.2f}%")
        print(f"Risk Amount      : {risk_amount:.2f}")
        print(f"AI Decision      : {ai_decision}")
        print(f"AI Score         : {ai_score}")
        print(f"Close Price      : {close_price:.2f}")
        print(f"ATR14            : {atr:.2f}")
        print(f"Stop Loss        : {stop_loss:.2f}")
        print(f"Take Profit      : {take_profit:.2f}")
        print(f"Position Size    : {position_size:.6f}")
        print(f"Position Value   : {position_value:.2f}")
        print("=" * 45)


def main():
    manager = RiskManager(
        "data/BTCUSDT/15m/BTCUSDT_15m.csv",
        account_size=10000,
        risk_per_trade=1.0
    )

    manager.load_csv()
    manager.calculate_risk()


if __name__ == "__main__":
    main()