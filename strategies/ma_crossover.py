# ma_crossover.py
import pandas as pd

class Strategy:
    """
    Simple Moving Average (SMA) crossover strategy.
    BUY when short SMA crosses above long SMA.
    SELL when short SMA crosses below long SMA.
    """

    def __init__(self, short_window=5, long_window=20):
        self.short_window = short_window
        self.long_window = long_window
        self.prices = []

    def generate_signal(self, market_data):
        # market_data is expected to be a price (float)
        self.prices.append(market_data)
        if len(self.prices) < self.long_window:
            return None  # not enough data yet

        df = pd.DataFrame(self.prices, columns=["price"])
        short_ma = df["price"].rolling(self.short_window).mean().iloc[-1]
        long_ma = df["price"].rolling(self.long_window).mean().iloc[-1]

        if short_ma > long_ma:
            return "BUY"
        elif short_ma < long_ma:
            return "SELL"
        else:
            return None
