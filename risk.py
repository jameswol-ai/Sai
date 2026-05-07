# risk.py
class RiskManager:
    def __init__(self, max_risk_pct=0.02, stop_loss_pct=0.01, take_profit_pct=0.02, max_drawdown_pct=0.10):
        self.max_risk_pct = max_risk_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.equity_peak = None

    def position_size(self, equity, price):
        risk_amount = equity * self.max_risk_pct
        return int(risk_amount / price)

    def check_stop_loss(self, entry_price, current_price):
        return current_price <= entry_price * (1 - self.stop_loss_pct)

    def check_take_profit(self, entry_price, current_price):
        return current_price >= entry_price * (1 + self.take_profit_pct)

    def check_drawdown(self, equity):
        if self.equity_peak is None:
            self.equity_peak = equity
        drawdown = (self.equity_peak - equity) / self.equity_peak
        return drawdown >= self.max_drawdown_pct
