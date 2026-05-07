from prometheus_client import Counter, Gauge, Histogram, start_http_server

# --- Metrics definitions ---
trades_executed = Counter("sai_trades_total", "Total number of trades executed")
pnl_gauge = Gauge("sai_pnl", "Current profit and loss")
latency_hist = Histogram("sai_trade_latency_seconds", "Latency per trade execution")

def start_metrics_server(port=8000):
    # Expose metrics endpoint at :8000/metrics
    start_http_server(port)

def record_trade(pnl, latency):
    trades_executed.inc()
    pnl_gauge.set(pnl)
    latency_hist.observe(latency)
