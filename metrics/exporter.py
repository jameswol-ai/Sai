# metrics/exporter.py
from prometheus_client import Gauge, Counter, start_http_server

# Gauges for real-time values
balance_gauge = Gauge("sai_balance", "Current account balance")
pnl_gauge = Gauge("sai_pnl", "Profit and Loss")
latency_gauge = Gauge("sai_trade_latency", "Trade execution latency (ms)")

# Counters for cumulative events
trade_counter = Counter("sai_trades_total", "Total trades executed")
error_counter = Counter("sai_errors_total", "Total errors encountered")

def start_metrics_server(port=8000):
    start_http_server(port)
    print(f"Prometheus metrics server running on port {port}")

def update_metrics(balance, pnl, latency, error=False):
    balance_gauge.set(balance)
    pnl_gauge.set(pnl)
    latency_gauge.set(latency)
    trade_counter.inc()
    if error:
        error_counter.inc()
