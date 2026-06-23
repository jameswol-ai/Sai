# streamlit_app.py

import streamlit as st
import threading, logging, time, atexit
import pandas as pd
import requests, random, os, csv
from prometheus_client import Gauge, Counter, make_wsgi_app, CollectorRegistry
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server

# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------
logging.basicConfig(filename="trading.log", level=logging.INFO, force=True)

# ---------------------------------------------------------
# Currency Map (East Africa + USD)
# ---------------------------------------------------------
CURRENCIES = {
    "USD": {"symbol": "$"},
    "SSP": {"symbol": "£"},
    "UGX": {"symbol": "USh"},
    "KES": {"symbol": "KSh"},
    "TZS": {"symbol": "TSh"},
    "RWF": {"symbol": "FRw"},
}

def get_fx_rate(base="USD", target="SSP"):
    try:
        url = f"https://api.exchangerate.host/latest?base={base}&symbols={target}"
        resp = requests.get(url).json()
        return resp["rates"][target]
    except Exception:
        return None

# ---------------------------------------------------------
# TradingBot
# ---------------------------------------------------------
class TradingBot:
    def __init__(self, currency="USD"):
        self.currency = currency
        self.position = 0
        self.balance = 1000

    def get_price(self):
        return round(100 + random.uniform(-1, 1), 4)

    def step(self, price):
        action = random.choice(["BUY", "SELL", "HOLD"])
        trade = None
        if action == "BUY":
            self.position += 1
            self.balance -= price
            trade = price
        elif action == "SELL" and self.position > 0:
            self.position -= 1
            self.balance += price
            trade = price
        return action, trade

    def convert_balance(self, fx_rates):
        rate = fx_rates.get(self.currency, 1.0)
        return round(self.balance * rate, 2)

# ---------------------------------------------------------
# Metrics
# ---------------------------------------------------------
class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.prices, self.actions, self.trades = [], [], []
        self.balance, self.pnl = 1000, 0
        self.balance_local, self.pnl_local = 1000, 0

    def update(self, price, action, trade, bot, fx_rates):
        with self._lock:
            self.prices.append(price)
            self.actions.append(action)
            self.trades.append(trade)
            self.balance = bot.balance
            self.pnl = bot.balance - 1000
            self.balance_local = bot.convert_balance(fx_rates)
            self.pnl_local = self.balance_local - (1000 * fx_rates.get(bot.currency, 1.0))

    def snapshot(self, bot, fx_rates):
        with self._lock:
            return {
                "last_price": self.prices[-1] if self.prices else None,
                "last_action": self.actions[-1] if self.actions else None,
                "balance_usd": self.balance,
                "balance_local": bot.convert_balance(fx_rates),
                "currency": bot.currency,
                "pnl_usd": self.pnl,
                "pnl_local": self.pnl_local,
                "prices": list(self.prices),
            }

# ---------------------------------------------------------
# CSV Exporter
# ---------------------------------------------------------
class CSVExporter:
    def __init__(self, filename="trades.csv"):
        self.filename = filename
        self._lock = threading.Lock()
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.filename):
            with open(self.filename, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp","price","action","trade",
                    "balance_usd","balance_local","currency",
                    "pnl_usd","pnl_local"
                ])

    def write_row(self, row):
        with self._lock:
            with open(self.filename, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    row["timestamp"], row["price"], row["action"], row["trade"],
                    row["balance_usd"], row["balance_local"], row["currency"],
                    row["pnl_usd"], row["pnl_local"]
                ])

# ---------------------------------------------------------
# Risk Plugin
# ---------------------------------------------------------
class RiskPlugin:
    def __init__(self, max_exposure_usd=5000):
        self.max_exposure_usd = max_exposure_usd

    def check(self, bot, last_price):
        exposure = bot.position * last_price
        if exposure > self.max_exposure_usd:
            return False, "Exposure limit exceeded"
        return True, None

# ---------------------------------------------------------
# Prometheus Metrics
# ---------------------------------------------------------
if "prom_registry" not in st.session_state:
    registry = CollectorRegistry()
    st.session_state["prom_registry"] = registry
    st.session_state["pnl_total"] = Gauge("sai_pnl_total", "Total Profit and Loss", registry=registry)
    st.session_state["trades_per_minute"] = Gauge("sai_trades_per_minute", "Trades executed per minute", registry=registry)
    st.session_state["trade_latency"] = Gauge("sai_trade_latency_seconds", "Latency per trade in seconds", registry=registry)
    st.session_state["open_positions"] = Gauge("sai_open_positions", "Number of open positions", registry=registry)
    st.session_state["model_version"] = Gauge("sai_model_version", "Current ML model version", registry=registry)
    st.session_state["trade_counter"] = Counter("sai_trade_count", "Total trades executed", registry=registry)

pnl_total = st.session_state["pnl_total"]
trades_per_minute = st.session_state["trades_per_minute"]
trade_latency = st.session_state["trade_latency"]
open_positions = st.session_state["open_positions"]
model_version = st.session_state["model_version"]
trade_counter = st.session_state["trade_counter"]

timestamps, pnl_history, trade_freq_history = [], [], []
MAX_HISTORY = 100

class ReusableWSGIServer(WSGIServer):
    allow_reuse_address = True

def start_metrics_server(port=8000):
    if "metrics_server" not in st.session_state:
        app = make_wsgi_app(st.session_state["prom_registry"])
        httpd = make_server("", port, app, server_class=ReusableWSGIServer, handler_class=WSGIRequestHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        st.session_state["metrics_server"] = httpd
        st.sidebar.success(f"✅ Prometheus metrics server running on port {port}")
        def shutdown_server():
            try:
                httpd.shutdown()
                httpd.server_close()
            except Exception:
                pass
        atexit.register(shutdown_server)
    else:
        st.sidebar.info(f"Prometheus metrics server already running on port {port}")

# ---------------------------------------------------------
# Alerts
# ---------------------------------------------------------
def trigger_alert(message, level="error"):
    if level == "error":
        st.error(message)
    elif level == "warning":
        st.warning(message)
    else:
        st.info(message)
    logging.warning(f"ALERT: {message}")

# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------
def render_dashboard():
    st.title("SAI Trading Dashboard")
    if pnl_total._value.get() < -1000:
        trigger_alert("⚠️ ALERT: Losses exceed $1000! Immediate review required.", level="error")
    if trade_latency._value.get() > 2.0:
        trigger_alert("⚠️ High latency detected (>2s per trade).", level="warning")
    if open_positions._value.get() > 10:
        trigger_alert("⚠️ Too many open positions. Risk exposure is high.", level="warning")

    col1, col2, col3 = st.columns(3)
    col1.metric("PnL ($)", f"{pnl_total._value.get():.2f}")
    col2.metric("Trades/min", f"{trades_per_minute._value.get():.0f}")
    col3.metric("Latency (s)", f"{trade_latency._value.get():.2f}")
    st.metric("Open Positions", f"{open_positions._value.get():.0f}")
    st.metric("Model Version", f"{model_version._value.get():.0f}")
    st.metric("Total Trades", f"{trade_counter._value.get():.0f}")

    timestamps.append(time.strftime("%H:%M:%S"))
    pnl_history.append(pnl_total._value.get())
    trade_freq_history.append(trades_per_minute._value.get())
    if len(timestamps) > MAX_HISTORY:
        timestamps.pop(0); pnl_history.pop(0); trade_freq_history.pop(0)

    if len(timestamps) > 1:
        df = pd.DataFrame({
            "Timestamp": timestamps,
            "PnL": pnl_history,
            "Trades/min": trade_freq_history
        })
        st.line_chart(df.set_index("Timestamp")[["PnL"]])
        st.line_chart(df.set_index("Timestamp")[["Trades/min"]])

# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():
    st.sidebar.title