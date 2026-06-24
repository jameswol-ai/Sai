import streamlit as st
import threading
import time
import logging
import pandas as pd
import matplotlib.pyplot as plt
from prometheus_client import Gauge, start_http_server

# ---------------------------
# Logging Setup
# ---------------------------
logging.basicConfig(
    filename="sai_trading.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ---------------------------
# Prometheus Metrics
# ---------------------------
trade_count = Gauge("sai_trade_count", "Number of trades executed")
profit_metric = Gauge("sai_profit", "Cumulative profit")

start_http_server(8000)

# ---------------------------
# Session State Initialization
# ---------------------------
if "trades" not in st.session_state:
    st.session_state.trades = []
if "running" not in st.session_state:
    st.session_state.running = False
if "profit" not in st.session_state:
    st.session_state.profit = 0.0

# ---------------------------
# Dummy Trading Loop
# ---------------------------
def trading_loop():
    while st.session_state.running:
        trade = {"time": time.strftime("%H:%M:%S"), "price": 100 + len(st.session_state.trades), "profit": 1.0}
        st.session_state.trades.append(trade)
        st.session_state.profit += trade["profit"]

        trade_count.set(len(st.session_state.trades))
        profit_metric.set(st.session_state.profit)

        logging.info(f"Trade executed: {trade}")
        time.sleep(2)

# ---------------------------
# Tabs
# ---------------------------
st.title("SAI Trading Bot Cockpit")

tabs = st.tabs(["Dashboard", "Strategy Config", "Logs", "Model Testing", "Debug"])

# Dashboard Tab
with tabs[0]:
    st.header("Live Dashboard")
    if st.button("Start Trading") and not st.session_state.running:
        st.session_state.running = True
        threading.Thread(target=trading_loop, daemon=True).start()
    if st.button("Stop Trading"):
        st.session_state.running = False

    st.metric("Total Trades", len(st.session_state.trades))
    st.metric("Cumulative Profit", f"${st.session_state.profit:.2f}")

    if st.session_state.trades:
        df = pd.DataFrame(st.session_state.trades)
        st.line_chart(df[["price", "profit"]])

# Strategy Config Tab
with tabs[1]:
    st.header("Strategy Configuration")
    risk_level = st.slider("Risk Level", 1, 10, 5)
    st.write(f"Selected Risk Level: {risk_level}")

# Logs Tab
with tabs[2]:
    st.header("Execution Logs")
    try:
        with open("sai_trading.log", "r") as f:
            logs = f.read()
        st.text_area("Logs", logs, height=300)
    except FileNotFoundError:
        st.warning("No logs yet.")

# Model Testing Tab
with tabs[3]:
    st.header("Model Testing")
    uploaded_file = st.file_uploader("Upload test dataset (CSV)", type="csv")
    if uploaded_file:
        df_test = pd.read_csv(uploaded_file)
        st.write(df_test.head())

# Debug Tab
with tabs[4]:
    st.header("Debug Panel")
    st.json({
        "running": st.session_state.running,
        "trades": len(st.session_state.trades),
        "profit": st.session_state.profit
    })
