# risk/manager.py
import logging

class RiskManager:
    def __init__(self, max_drawdown=0.2, stop_loss=0.05, max_position_size=0.1):
        self.max_drawdown = max_drawdown
        self.stop_loss = stop_loss
        self.max_position_size = max_position_size
        self.initial_balance = None
        self.current_balance = None

    def set_initial_balance(self, balance):
        self.initial_balance = balance
        self.current_balance = balance

    def update_balance(self, balance):
        self.current_balance = balance

    def check_trade(self, trade_price, entry_price, position_size, balance):
        # Stop-loss check
        if (trade_price - entry_price) / entry_price <= -self.stop_loss:
            logging.warning("Stop-loss triggered. Trade blocked.")
            return False

        # Position sizing check
        if position_size / balance > self.max_position_size:
            logging.warning("Position size exceeds limit. Trade blocked.")
            return False

        # Drawdown check
        if self.initial_balance and (balance - self.initial_balance) / self.initial_balance <= -self.max_drawdown:
            logging.warning("Max drawdown breached. Trading halted.")
            return False

        return True
