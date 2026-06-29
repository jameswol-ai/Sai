import streamlit as st
import threading
import time
import logging
import pandas as pd
from prometheus_client import Counter, Gauge, start_http_server

# --- Prometheus Metrics ---
trade_counter = Counter("sai_trades_total", "Total trades executed")
price_gauge = Gauge("sai_last_price", "Last trade price")
exposure_gauge = Gauge("sai_exposure", "Current exposure")
loss_gauge = Gauge("sai_loss", "Current loss")

# Start Prometheus metrics server on port 8000
start_http_server(8000)

# --- Logging ---
logging.basicConfig(
    filename="sai_trading.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Session State Defaults ---
defaults = {
    "trades": [],
    "prices": [],
    "running": False,
    "risk_limits": {"max_loss": 50, "max_exposure": 1000}
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- Trading Loop ---
def trading_loop():
    while st.session_state.running:
        price = 100 + (time.time() % 10)  # mock price
        trade = {"time": time.strftime("%H:%M:%S"), "price": price}
        st.session_state.prices.append(price)

        # Prometheus metrics update
        price_gauge.set(price)
        exposure_gauge.set(len(st.session_state.trades))

        # Risk enforcement
        if len(st.session_state.trades) < st.session_state["risk_limits"]["max_exposure"]:
            st.session_state.trades.append(trade)
            trade_counter.inc()
            logging.info(f"Trade executed: {trade}")
        else:
            loss_gauge.set(st.session_state["risk_limits"]["max_loss"])
            logging.warning("Exposure limit reached, trade skipped.")

        time.sleep(2)

# --- Dashboard Tab ---
def dashboard_tab():
    st.header("Live Trading Dashboard")
    col1, col2 = st.columns(2)
    if col1.button("Start Trading") and not st.session_state.running:
        st.session_state.running = True
        threading.Thread(target=trading_loop, daemon=True).start()
        st.success("Trading loop started.")
    if col2.button("Stop Trading") and st.session_state.running:
        st.session_state.running = False
        st.warning("Trading loop stopped.")

    if st.session_state.trades:
        df = pd.DataFrame(st.session_state.trades)
        st.line_chart(df["price"])
        st.dataframe(df)

# --- Strategy Config Tab ---
def strategy_tab():
    st.header("Strategy Configuration")
    st.session_state["risk_limits"]["max_loss"] = st.slider("Max Loss", 10, 100, 50)
    st.session_state["risk_limits"]["max_exposure"] = st.slider("Max Exposure", 100, 5000, 1000)
    st.text_input("Strategy Name", "Default Strategy")

# --- Logs Tab ---
def logs_tab():
    st.header("Execution Logs")
    try:
        with open("sai_trading.log") as f:
            logs = f.read()
        st.text_area("Log Output", logs, height=300)
    except FileNotFoundError:
        st.info("No logs yet.")

# --- Model Testing Tab ---
def model_tab():
    st.header("Model Testing")
    st.file_uploader("Upload Model File", type=["pkl"])
    st.button("Run Backtest")

# --- Debug Tab ---
def debug_tab():
    st.header("Debugging Tools")
    st.json({
        "recent_trades": st.session_state.trades[-5:],
        "recent_prices": st.session_state.prices[-5:],
        "risk_limits": st.session_state["risk_limits"]
    })

# --- Main App ---
def main():
    st.title("Sai Trading Bot Cockpit")
    tabs = {
        "Dashboard": dashboard_tab,
        "Strategy Config": strategy_tab,
        "Logs": logs_tab,
        "Model Testing": model_tab,
        "Debug": debug_tab,
    }
    choice = st.sidebar.radio("Navigation", list(tabs.keys()))
    tabs[choice]()

if __name__ == "__main__":
    main()
