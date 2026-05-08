# risk/plugins/max_drawdown.py
from .base import RiskPlugin

class MaxDrawdownPlugin(RiskPlugin):
    def __init__(self, max_drawdown=0.2, initial_balance=None):
        self.max_drawdown = max_drawdown
        self.initial_balance = initial_balance

    def check(self, trade, balance):
        if not self.initial_balance:
            self.initial_balance = balance
        return (balance - self.initial_balance) / self.initial_balance > -self.max_drawdown
