# risk/plugins/base.py
class RiskPlugin:
    def check(self, trade, balance):
        """Return True if trade is allowed, False otherwise"""
        raise NotImplementedError
