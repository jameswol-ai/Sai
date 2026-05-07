import streamlit as st
import time
import random
import threading
import logging
import http.server
import socketserver
from prometheus_client import Gauge, CollectorRegistry, generate_latest

# --- Logging Setup ---
logging.basicConfig(
    filename="trading.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# --- Prometheus Metrics ---
registry = CollectorRegistry()
equity_gauge = Gauge("sai_equity", "Current equity", registry=registry)
drawdown_gauge = Gauge("sai_drawdown", "Current drawdown", registry=registry)
sharpe_gauge = Gauge("sai_sharpe", "Sharpe ratio", registry=registry)
tracker_gauge = Gauge("sai_tracker_completion", "Project tracker completion", registry=registry)

# --- Session State Defaults ---
def init_defaults():
    defaults = {
        "balance": 1000.0,
        "pnl": 0.0,
        "last_price": None,
        "last_action": None,
        "running": False,
        "prices": [],
        "tracker_completion": 0,
        "metrics_server_started": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# --- Trading Loop ---
def trading_loop(refresh):
    while st.session_state.running:
        price = round(random.uniform(90, 110), 2)
        action = random.choice(["BUY", "SELL", "HOLD"])
        pnl_change = random.uniform(-1, 1)

        st.session_state.last_price = price
        st.session_state.last_action = action
        st.session_state.pnl += pnl_change
        st.session_state.balance += pnl_change
        st.session_state.prices.append(price)
        st.session_state.tracker_completion = min(100, st.session_state.tracker_completion + random.uniform(0, 2))

        # Update Prometheus metrics
        equity_gauge.set(st.session_state.balance)
        drawdown_gauge.set(max(0, (1000 - st.session_state.balance) / 1000))
        sharpe_gauge.set(random.uniform(-1, 2))
        tracker_gauge.set(st.session_state.tracker_completion)

        logging.info(f"Price={price}, Action={action}, Balance={st.session_state.balance:.2f}, PnL={st.session_state.pnl:.2f}")
        time.sleep(refresh)

# --- Prometheus HTTP Handler ---
class MetricsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(generate_latest(registry))
        else:
            self.send_response(404)
            self.end_headers()

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def start_metrics_server(port=8000):
    if not st.session_state.get("metrics_server_started", False):
        server = ReusableTCPServer(("", port), MetricsHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        st.session_state.metrics_server_started = True
        st.write(f"✅ Prometheus metrics server running on port {port}")

# --- Dashboard Tab ---
def dashboard_tab():
    st.subheader("Live Trading Controls")
    refresh = st.number_input("Refresh interval (s)", min_value=0.5, value=1.0, step=0.5)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Start Trading"):
            st.session_state.running = True
            threading.Thread(target=trading_loop, args=(refresh,), daemon=True).start()
    with col2:
        if st.button("⏹ Stop Trading"):
            st.session_state.running = False

    st.subheader("Live Metrics")
    st.metric("Last Price", st.session_state.last_price if st.session_state.last_price else "—")
    st.metric("Last Action", st.session_state.last_action if st.session_state.last_action else "—")
    st.metric("Balance", f"{st.session_state.balance:.2f}")
    st.metric("PnL", f"{st.session_state.pnl:.2f}")

    chart = st.empty()
    if st.session_state.prices:
        chart.line_chart(st.session_state.prices[-50:])

# --- Strategy Tab ---
def strategy_tab():
    st.subheader("Strategy Configuration")
    st.text_input("Strategy Name", "Default Strategy")
    st.slider("Risk Level", 1, 10, 5)
    st.checkbox("Enable Stop Loss", True)

# --- Logs Tab ---
def logs_tab():
    st.subheader("Logs")
    try:
        with open("trading.log") as f:
            st.text_area("Execution Logs", f.read(), height=300)
    except FileNotFoundError:
        st.text_area("Execution Logs", "No logs yet...", height=300)

# --- Debug Tab ---
def debug_tab():
    st.subheader("Debug Info")
    st.write("Session State:", dict(st.session_state))

# --- Analytics Tab ---
def analytics_tab():
    st.subheader("Analytics")
    st.metric("Sharpe Ratio", f"{sharpe_gauge._value.get():.2f}")
    st.metric("Max Drawdown", f"{drawdown_gauge._value.get():.2%}")

# --- Registry Tab ---
def registry_tab():
    st.subheader("Model Registry")
    st.table({
        "Model": ["Default", "Experimental"],
        "Accuracy": [0.65, 0.72],
        "Sharpe": [1.1, 1.4]
    })

# --- Alerts Tab ---
def alerts_tab():
    st.subheader("Active Alerts")
    if drawdown_gauge._value.get() > 0.10:
        st.error("⚠️ High Drawdown > 10%")
    if equity_gauge._value.get() < 10000:
        st.warning("⚠️ Equity dropped below $10,000")
    if tracker_gauge._value.get() == 100:
        st.success("✅ Project category completed")

# --- Main App ---
def main():
    init_defaults()
    start_metrics_server(port=8000)  # Prometheus scrapes here
    st.title("SAI Trading Dashboard Cockpit")

    tabs = st.tabs([
        "📊 Dashboard",
        "🧠 Strategy",
        "📜 Logs",
        "🛠 Debug",
        "📈 Analytics",
        "📂 Registry",
        "🚨 Alerts"
    ])

    with tabs[0]:
        dashboard_tab()
    with tabs[1]:
        strategy_tab()
    with tabs[2]:
        logs_tab()
    with tabs[3]:
        debug_tab()
    with tabs[4]:
        analytics_tab()
    with tabs[5]:
        registry_tab()
    with tabs[6]:
        alerts_tab()

if __name__ == "__main__":
    main()
