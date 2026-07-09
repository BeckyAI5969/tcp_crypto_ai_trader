class PortfolioScheduler:

    def __init__(self):
        self.current_bar = 0

    def next(self):
        self.current_bar += 1
        return self.current_bar

    def reset(self):
        self.current_bar = 0