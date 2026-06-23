import streamlit as st
import threading
import logging
import time
import pandas as pd

# --- Prometheus Metrics ---
from prometheus_client import Gauge, Counter, make_wsgi_app
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler

# Define metrics
pnl_total = Gauge("sai_pnl_total", "Total Profit and Loss")
trades_per_minute = Gauge("sai_trades_per_minute", "Trades executed per minute")
trade_latency = Gauge("sai_trade_latency_seconds", "Latency per trade in seconds")
open_positions = Gauge("sai_open_positions", "Number of open positions")
model_version = Gauge("sai_model_version", "Current ML model version")
trade_counter = Counter("sai_trade_count", "Total trades executed")

# History buffers for charts
timestamps, pnl_history, trade_freq_history = [], [], []

class ReusableWSGIServer(WSGIServer):
    allow_reuse_address = True

def start_metrics_server(port=8000, registry=None):
    if "metrics_server_started" not in st.session_state:
        app = make_wsgi_app(registry=registry)
        httpd = ReusableWSGIServer(("", port), WSGIRequestHandler)
        httpd.set_app(app)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        st.session_state["metrics_server_started"] = True
        st.sidebar.success(f"✅ Prometheus metrics server running on port {port}")

# Configure logging
logging.basicConfig(filename="trading.log", level=logging.INFO)

# Unified alert trigger
def trigger_alert(message, level="error"):
    # Show banner
    if level == "error":
        st.error(message)
    elif level == "warning":
        st.warning(message)
    else:
        st.info(message)

    # Notify via plugins
    for notifier in notifier_plugins:
        if notifier.active:
            try:
                notifier.send(message)
            except Exception as e:
                logging.error(f"Notifier failed: {notifier.name} - {e}")

    # Log alert
    logging.warning(f"ALERT: {message}")

def render_dashboard():
    st.title("SAI Trading Dashboard")

    if st.button("Start Trading"):
        if "trading_thread" not in st.session_state or not st.session_state.trading_thread.is_alive():
            st.session_state.trading_thread = threading.Thread(target=run_trading_loop, daemon=True)
            st.session_state.trading_thread.start()
            st.success("Trading loop started.")
        else:
            st.warning("Trading loop already running.")

    # 🚨 Alerts wired to notifiers
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

    # Charts
    if len(timestamps) > 1:
        df = pd.DataFrame({
            "Timestamp": timestamps,
            "PnL": pnl_history,
            "Trades/min": trade_freq_history
        })
        st.line_chart(df.set_index("Timestamp")[["PnL"]])
        st.line_chart(df.set_index("Timestamp")[["Trades/min"]])

def render_strategy_config():
    st.title("Strategy Configuration")
    st.write("Configure your trading strategies here.")

def render_logs():
    st.title("Logs")
    try:
        with open("trading.log", "r") as f:
            logs = f.read()
        st.text_area("Log Output", logs, height=400)
    except FileNotFoundError:
        st.warning("No logs found yet.")

def render_model_testing():
    st.title("Model Testing")
    st.write("Run backtests and model evaluations here.")

def render_debug():
    st.title("Debug Tools")
    st.write("Diagnostics and debugging utilities.")

def render_plugins_tab():
    st.title("Plugin Control Center")

    # Risk Management Plugins
    st.header("Risk Management")
    for plugin in risk_plugins:
        enabled = st.checkbox(f"Enable {plugin.name}", value=plugin.enabled, key=f"{plugin.name}_enabled")
        param = st.slider(
            f"{plugin.name} threshold",
            plugin.min_val,
            plugin.max_val,
            plugin.default,
            key=f"{plugin.name}_param"
        )
        plugin.update(enabled=enabled, param=param)

    # Strategy Switcher
    st.header("Strategy")
    strategy_choice = st.selectbox("Select Strategy", [s.name for s in strategy_plugins], key="strategy_choice")
    strategy_plugins[strategy_choice].activate()

    # Notifier Controls
    st.header("Notifications")
    for notifier in notifier_plugins:
        active = st.checkbox(f"Enable {notifier.name}", value=notifier.active, key=f"{notifier.name}_active")
        if st.button(f"Test {notifier.name}", key=f"{notifier.name}_test"):
            notifier.test_ping()
        notifier.update(active=active)

    # Audit Log
    st.header("Audit Log")
    st.write("Recent plugin actions and parameter changes will appear here.")

def main():
    st.sidebar.title("SAI Cockpit")
    tab = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Strategy Config", "Logs", "Model Testing", "Debug", "Plugins"]
    )
# --- Prometheus Metrics Server Guard ---
class ReusableWSGIServer(WSGIServer):
    allow_reuse_address = True

def start_metrics_server(port=8000, registry=None):
    if "metrics_server" not in st.session_state:
        app = make_wsgi_app(registry=registry)
        httpd = ReusableWSGIServer(("", port), WSGIRequestHandler)
        httpd.set_app(app)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        st.session_state["metrics_server"] = httpd
        st.sidebar.success(f"✅ Prometheus metrics server running on port {port}")


    if tab == "Dashboard":
        render_dashboard()
    elif tab == "Strategy Config":
        render_strategy_config()
    elif tab == "Logs":
        render_logs()
    elif tab == "Model Testing":
        render_model_testing()
    elif tab == "Debug":
        render_debug()
    elif tab == "Plugins":
        render_plugins_tab()

if __name__ == "__main__":
    main()

def main():
    st.sidebar.title("SAI Cockpit")
    tab = st.sidebar.radio(
        "Navigation",
        ["Dashboard", "Strategy Config", "Logs", "Model Testing", "Debug", "Plugins"]
    )

    # Start Prometheus metrics server once
    start_metrics_server(port=8000)

    if tab == "Dashboard":
        render_dashboard()
    elif tab == "Strategy Config":
        render_strategy_config()
    elif tab == "Logs":
        render_logs()
    elif tab == "Model Testing":
        render_model_testing()
    elif tab == "Debug":
        render_debug()
    elif tab == "Plugins":
        render_plugins_tab()
