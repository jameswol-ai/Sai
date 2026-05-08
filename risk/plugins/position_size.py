# risk/plugins/position_size.py
from .base import RiskPlugin

class PositionSizePlugin(RiskPlugin):
    def __init__(self, max_fraction=0.10):
        """
        max_fraction: maximum fraction of account balance allowed per trade
        e.g. 0.10 = 10%
        """
        self.max_fraction = max_fraction

    def check(self, trade, balance):
        """
        trade: dict with keys {"size": float}
        balance: current account balance
        """
        position_fraction = trade["size"] / balance
        return position_fraction <= self.max_fraction
