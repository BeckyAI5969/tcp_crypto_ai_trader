class PaperPortfolio:

    def __init__(self, initial_capital=100000):
        self.initial_capital = float(initial_capital)
        self.cash = float(initial_capital)
        self.realized_pnl = 0.0
        self.equity_history = []

    def can_open(self, capital_required):
        return self.cash >= capital_required

    def open_position(self, capital_required):
        if not self.can_open(capital_required):
            return False

        self.cash -= capital_required
        return True

    def close_position(self, capital_used, pnl):
        self.cash += capital_used + pnl
        self.realized_pnl += pnl

    def equity(self, unrealized_pnl=0.0):
        return self.cash + unrealized_pnl

    def record(self, timestamp, unrealized_pnl=0.0, open_positions=0):
        self.equity_history.append({
            "time": timestamp,
            "cash": round(self.cash, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "equity": round(self.equity(unrealized_pnl), 2),
            "open_positions": open_positions,
        })

    def history(self):
        return self.equity_history