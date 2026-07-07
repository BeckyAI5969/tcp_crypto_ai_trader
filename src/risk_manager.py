class RiskManager:

    def __init__(self, balance, risk_percent):
        self.balance = balance
        self.risk_percent = risk_percent

    def round_step_size(self, quantity, step_size):
        return int(quantity / step_size) * step_size

    def calculate_position_size(
        self,
        entry_price,
        stop_loss,
        step_size=0.001
    ):
        risk_amount = self.balance * self.risk_percent / 100
        loss_per_btc = abs(entry_price - stop_loss)

        if loss_per_btc == 0:
            return 0

        qty = risk_amount / loss_per_btc
        qty = self.round_step_size(qty, step_size)

        return round(qty, 3)


def main():
    risk = RiskManager(
        balance=5000,
        risk_percent=1
    )

    qty = risk.calculate_position_size(
        entry_price=64000,
        stop_loss=63500,
        step_size=0.001
    )

    print("=" * 50)
    print("Risk Manager")
    print("=" * 50)
    print("Position Size :", qty, "BTC")
    print("=" * 50)


if __name__ == "__main__":
    main()