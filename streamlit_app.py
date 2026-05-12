import streamlit as st
import threading
import time
import random
import logging
import pandas as pd
from prometheus_client import Gauge, CollectorRegistry, start_http_server

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

def start_metrics_server(port=8000):
    if st.session_state.get("metrics_server_started", False):
        return
    try:
        start_http_server(port, registry=registry)
        st.session_state.metrics_server_started = True
        st.session_state.metrics_port = port
        st.write(f"✅ Prometheus metrics server running on port {port}")
    except OSError as e:
        st.warning(f"⚠️ Port {port} unavailable ({e}). Trying fallback port {port+1}...")
        try:
            start_http_server(port + 1, registry=registry)
            st.session_state.metrics_server_started = True
            st.session_state.metrics_port = port + 1
            st.write(f"✅ Prometheus metrics server running on port {port+1}")
        except OSError as e2:
            st.error(f"❌ Failed to start metrics server: {e2}")

# --- Risk Plugins (stubs) ---
class StopLossPlugin: 
    def __init__(self, threshold=0.05): self.threshold = threshold
    def check(self, trade, balance): return True

class MaxDrawdownPlugin: 
    def __init__(self, max_drawdown=0.2): self.max_drawdown = max_drawdown
    def check(self, trade, balance): return True

class PositionSizePlugin: 
    def __init__(self, max_fraction=0.1): self.max_fraction = max_fraction
    def check(self, trade, balance): return True

# --- Email Notifier (stub) ---
class EmailNotifier:
    def notify_pipeline(self, status, commit, branch):
        logging.info(f"EmailNotifier: {status} {commit} {branch}")

# --- Session State Defaults ---
def init_defaults():
    defaults = {
        "balance": 1000.0,
        "pnl": 0.0,
        "last_price": None,
        "last_action": None,
        "running": False,
        "prices": [],
        "trades": [],
        "alerts": [],
        "tracker_completion": 0,
        "risk_manager": [],
        "notifier": None,
        "metrics_server_started": False,
        "metrics_port": None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def init_risk_manager():
    st.session_state.risk_manager = [
        StopLossPlugin(threshold=0.05),
        MaxDrawdownPlugin(max_drawdown=0.20),
        PositionSizePlugin(max_fraction=0.10)
    ]

def init_notifier():
    st.session_state.notifier = EmailNotifier()

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
        st.session_state.trades.append({
            "timestamp": pd.Timestamp.now(),
            "price": price,
            "action": action,
            "profit": pnl_change
        })

        equity_gauge.set(st.session_state.balance)
        drawdown_gauge.set(max(0, (1000 - st.session_state.balance) / 1000))
        sharpe_gauge.set(random.uniform(-1, 2))
        tracker_gauge.set(min(100, st.session_state.tracker_completion + random.uniform(0, 2)))

        logging.info(f"Price={price}, Action={action}, Balance={st.session_state.balance:.2f}, PnL={st.session_state.pnl:.2f}")
        time.sleep(refresh)

# --- Tabs ---
def dashboard_tab():
    st.subheader("Live Trading Controls")
    refresh = st.number_input("Refresh interval (s)", min_value=0.5, value=1.0, step=0.5)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Start Trading"):
            if not st.session_state.running:
                st.session_state.running = True
                threading.Thread(target=trading_loop, args=(refresh,), daemon=True).start()
    with col2:
        if st.button("⏹ Stop Trading"):
            st.session_state.running = False

    st.metric("Last Price", st.session_state.last_price or "—")
    st.metric("Last Action", st.session_state.last_action or "—")
    st.metric("Balance", f"{st.session_state.balance:.2f}")
    st.metric("PnL", f"{st.session_state.pnl:.2f}")
    if st.session_state.prices:
        st.line_chart(st.session_state.prices[-50:])

def strategy_tab():
    st.subheader("Strategy Configuration")
    st.text_input("Strategy Name", "Default Strategy")
    st.slider("Risk Level", 1, 10, 5)
    st.checkbox("Enable Stop Loss", True)

def logs_tab():
    st.subheader("Logs")
    try:
        with open("trading.log") as f:
            st.text_area("Execution Logs", f.read(), height=300)
    except FileNotFoundError:
        st.text_area("Execution Logs", "No logs yet...", height=300)

def debug_tab():
    st.subheader("Debug Info")
    st.write("Session State:", dict(st.session_state))

def analytics_tab():
    st.subheader("Analytics")
    st.metric("Sharpe Ratio", f"{sharpe_gauge._value.get():.2f}")
    st.metric("Max Drawdown", f"{drawdown_gauge._value.get():.2%}")

def registry_tab():
    st.subheader("Model Registry")
    st.table(pd.DataFrame({
        "Model": ["Default", "Experimental"],
        "Accuracy": [0.65, 0.72],
        "Sharpe": [1.1, 1.4]
    }))

def alerts_tab():
    st.subheader("Active Alerts")
    if drawdown_gauge._value.get() > 0.10:
        st.error("⚠️ High Drawdown > 10%")
    if equity_gauge._value.get() < 10000:
        st.warning("⚠️ Equity dropped below $10,000")
    if tracker_gauge._value.get() == 100:
        st.success("✅ Project category completed")

def helm_tab():
    st.subheader("Helm Chart Deployment")
    st.markdown("""
    Use the provided Helm chart bundle to deploy Prometheus, Grafana, and Alertmanager:

    ```bash
    helm repo add sai-monitoring https://yourdomain.com/charts
    helm install sai-monitoring sai-monitoring/sai-chart -f values-production.yaml
    ```

    Once deployed, access monitoring at:
    - Prometheus → `/prometheus`
    - Grafana → `/grafana`
    - Alertmanager → `/alertmanager`
    """)

# --- Main App ---
def main():
    init_defaults()
    init_risk_manager()
    init_notifier()
    start_metrics_server(port=8000)

    st.title("SAI Trading Dashboard Cockpit")
    tabs = st.tabs([
        "📊 Dashboard", "🧠 Strategy", "📜 Logs", "🛠 Debug", "📈 Analytics", "📦 Registry", "🚨 Alerts", "📦 Helm"
    ])
    with tabs[0]: dashboard_tab()
    with tabs[1]: strategy_tab()
    with tabs[2]: logs_tab()
    with tabs[3]: debug_tab()
    with tabs[4]: analytics_tab()
    with tabs[5]: registry_tab()
    with tabs[6]: alerts_tab()
    with tabs[7]: helm_tab()

if __name__ == "__main__":
    main()
