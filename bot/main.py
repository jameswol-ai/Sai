import random
import sai

from engine.core_loop import SaiCoreLoop
from sai.core.engine import StrategyPlugin

plugin = StrategyPlugin("sai.strategies.ml_strategy")
signal = plugin.generate_signal(101.5)
print("Generated signal:", signal)

loop = SaiCoreLoop(bot, metrics, csv_exporter, sleep_time=1.0)

try:
    loop.start(on_update=None)
except KeyboardInterrupt:
    loop.stop()
    print("Stopped by user")

snap, metrics, chart = engine.run_cycle()

print(
    f"[{snap['cycle']}] "
    f"Price: {snap['price']} | "
    f"Signal: {snap['signal']} | "
    f"PnL: {snap['pnl']} | "
    f"Bal: {snap['balance']} | "
    f"Sharpe: {metrics['sharpe']} | "
    f"WinRate: {metrics['win_rate']}"
)

print(chart)

def get_data():
    """Simulate fetching a price feed (replace with real API)."""
    return round(100 + random.uniform(-1, 1), 2)

def run_bot(engine, price):
    """Run a simple trading decision (replace with strategy logic)."""
    decision = "BUY" if price < 100 else "SELL"
    trade = {"time": engine.current_time(), "price": price, "decision": decision}
    engine.record_trade(trade)
    return trade
