# sai/core/engine.py

# engine.py (excerpt)

import logging
import importlib

class StrategyPlugin:
    def __init__(self, module_name, class_name="Strategy"):
        try:
            module = importlib.import_module(module_name)
            self.strategy = getattr(module, class_name)()
        except Exception as e:
            logging.error(f"Failed to load strategy {module_name}: {e}")
            self.strategy = None

    def generate_signal(self, market_data):
        if self.strategy:
            try:
                return self.strategy.generate_signal(market_data)
            except Exception as e:
                logging.error(f"Signal error: {e}")
        return None

from sai.core.performance import PerformanceSnapshot
from sai.core.metrics import RollingMetrics
from sai.core.equity_chart import EquityCurveASCII
from sai.broker.simulated_broker import SimulatedBroker

broker = SimulatedBroker(
    starting_balance=1000,
    spread=0.02,
    slippage_pct=0.0005,
    latency_ms=80,
    fill_probability=0.98
)

class TradingEngine:
    def __init__(self, model, broker):
        self.model = model
        self.broker = broker
        self.cycle = 0
        self.snapshot = PerformanceSnapshot()

    def run_cycle(self):
        self.cycle += 1

        price = self.broker.get_price()
        signal = self.model.predict(price)
        position, pnl, balance = self.broker.execute(signal)

        snap = self.snapshot.log(
            cycle=self.cycle,
            price=price,
            signal=signal,
            position=position,
            pnl=pnl,
            balance=balance
        )

        return snap

class Sai:
    """
    Minimal trading bot stub for Streamlit integration.
    """

    def __init__(self, starting_balance: float = 10000.0, risk: int = 5):
        self.balance = starting_balance
        self.risk = risk
        self.open_trades = []
        self._counter = 0  # internal counter instead of random

    def run_once(self):
        """
        Simulates one trading step deterministically.
        Every 3rd call opens a trade.
        """
        self._counter += 1
        if self._counter % 3 == 0:
            trade = {
                "id": len(self.open_trades) + 1,
                "amount": 100 + 50 * (self._counter % 5),  # simple pattern
                "direction": "BUY" if self._counter % 2 == 0 else "SELL"
            }
            self.open_trades.append(trade)
            # balance oscillates up/down
            self.balance += (-25 if self._counter % 2 else 25)
            return f"Trade {trade['id']}: {trade['direction']} ${trade['amount']} | Balance: ${self.balance:.2f}"
        return None

class TradingEngine:
    def __init__(self, model, broker):
        self.model = model
        self.broker = broker
        self.cycle = 0
        self.snapshot = PerformanceSnapshot()
        self.metrics = RollingMetrics()

    def run_cycle(self):
        self.cycle += 1

        price = self.broker.get_price()
        signal = self.model.predict(price)
        position, pnl, balance = self.broker.execute(signal)

        snap = self.snapshot.log(
            cycle=self.cycle,
            price=price,
            signal=signal,
            position=position,
            pnl=pnl,
            balance=balance
        )

        metrics = self.metrics.update(balance)

        return snap, metrics

class TradingEngine:
    def __init__(self, model, broker):
        self.model = model
        self.broker = broker
        self.cycle = 0
        self.snapshot = PerformanceSnapshot()
        self.metrics = RollingMetrics()
        self.chart = EquityCurveASCII()

    def run_cycle(self):
        self.cycle += 1

        price = self.broker.get_price()
        signal = self.model.predict(price)
        position, pnl, balance = self.broker.execute(signal)

        snap = self.snapshot.log(
            cycle=self.cycle,
            price=price,
            signal=signal,
            position=position,
            pnl=pnl,
            balance=balance
        )

        metrics = self.metrics.update(balance)
        chart = self.chart.update(balance)

        return snap, metrics, chart
