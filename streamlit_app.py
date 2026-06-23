import streamlit as st
import threading
import logging
import time
import pandas as pd
import atexit

# --- Prometheus Metrics ---
from prometheus_client import Gauge, Counter, make_wsgi_app, CollectorRegistry
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler

# Configure logging
logging.basicConfig(filename="trading.log", level=logging.INFO, force=True)

# --- Registry & Metrics Guard ---
if "prom_registry" not in st.session_state:
    registry = CollectorRegistry()
    st.session_state["prom_registry"] = registry

    st.session_state["pnl_total"] = Gauge("sai_pnl_total", "Total Profit and Loss", registry=registry)
    st.session_state["trades_per_minute"] = Gauge("sai_trades_per_minute", "Trades executed per minute", registry=registry)
    st.session_state["trade_latency"] = Gauge("sai_trade_latency_seconds", "Latency per trade in seconds", registry=registry)
    st.session_state["open_positions"] = Gauge("sai_open_positions", "Number of open positions", registry=registry)
    st.session_state["model_version"] = Gauge("sai_model_version", "Current ML model version", registry=registry)
    st.session_state["trade_counter"] = Counter("sai_trade_count", "Total trades executed", registry=registry)

# Aliases
pnl_total = st.session_state["pnl_total"]
trades_per_minute = st.session_state["trades_per_minute"]
trade_latency = st.session_state["trade_latency"]
open_positions = st.session_state["open_positions"]
model_version = st.session_state["model_version"]
trade_counter = st.session_state["trade_counter"]

# History buffers
timestamps, pnl_history, trade_freq_history = [], [], []
MAX_HISTORY = 100

# --- Metrics Server Guard ---
class ReusableWSGIServer(WSGIServer):
    allow_reuse_address = True

def start_metrics_server(port=8000):
    if "metrics_server" not in st.session_state:
        httpd.set_app(app)

        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()

        st.session_state["metrics_server"] = httpd
        st.sidebar.success(f"✅ Prometheus metrics server running on port {port}")

        # Shutdown hook
        def shutdown_server():
            try:
                httpd.shutdown()
                httpd.server_close()
            except Exception:
                pass
        atexit.register(shutdown_server)
    else:
        st.sidebar.info(f"Prometheus metrics server already running on port {port}")

# --- Alerts ---
def trigger_alert(message, level="error"):
    if level == "error":
        st.error(message)
    elif level == "warning":
        st.warning(message)
    else:
        st.info(message)
    logging.warning(f"ALERT: {message}")

# --- Dashboard ---
def render_dashboard():
    st.title("SAI Trading Dashboard")

    # 🚨 Alerts
    if pnl_total._value.get() < -1000:
        trigger_alert("⚠️ ALERT: Losses exceed $1000! Immediate review required.", level="error")
    if trade_latency._value.get() > 2.0:
        trigger_alert("⚠️ High latency detected (>2s per trade).", level="warning")
    if open_positions._value.get() > 10:
        trigger_alert("⚠️ Too many open positions. Risk exposure is high.", level="warning")

    # Snapshot metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("PnL ($)", f"{pnl_total._value.get():.2f}")
    col2.metric("Trades/min", f"{trades_per_minute._value.get():.0f}")
    col3.metric("Latency (s)", f"{trade_latency._value.get():.2f}")
    st.metric("Open Positions", f"{open_positions._value.get():.0f}")
    st.metric("Model Version", f"{model_version._value.get():.0f}")
    st.metric("Total Trades", f"{trade_counter._value.get():.0f}")

    # Update history buffers
    timestamps.append(time.strftime("%H:%M:%S"))
    pnl_history.append(pnl_total._value.get())
    trade_freq_history.append(trades_per_minute._value.get())
    if len(timestamps) > MAX_HISTORY:
        timestamps.pop(0); pnl_history.pop(0); trade_freq_history.pop(0)

    # Charts
    if len(timestamps) > 1:
        df = pd.DataFrame({
            "Timestamp": timestamps,
            "PnL": pnl_history,
            "Trades/min": trade_freq_history
        })
        st.line_chart(df.set_index("Timestamp")[["PnL"]])
        st.line_chart(df.set_index("Timestamp")[["Trades/min"]])

# --- Main ---
def main():
    st.sidebar.title("SAI Cockpit")
        ["Navigation","Dashboard", "Strategy Config", "Logs", "Model Testing", "Debug", "Plugins"]

    if tab == "Dashboard":
        render_dashboard()
    elif tab == "Strategy Config":
        st.title("Strategy Configuration")
    elif tab == "Logs":
        st.title("Logs")
    elif tab == "Model Testing":
        st.title("Model Testing")
    elif tab == "Debug":
        st.title("Debug Tools")
    elif tab == "Plugins":
        st.title("Plugin Control Center")


