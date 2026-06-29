import streamlit as st
import threading
import time
import logging
import pandas as pd
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(
    filename="sai_trading.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Initialize session state
if "trades" not in st.session_state:
    st.session_state.trades = []
if "prices" not in st.session_state:
    st.session_state.prices = []
if "running" not in st.session_state:
    st.session_state.running = False

# Dummy trading loop
def trading_loop():
    while st.session_state.running:
        price = 100 + (time.time() % 10)  # mock price
        trade = {"time": time.strftime("%H:%M:%S"), "price": price}
        st.session_state.prices.append(price)
        st.session_state.trades.append(trade)
        logging.info(f"Trade executed: {trade}")
        time.sleep(2)

# Dashboard tab
def dashboard_tab():
    st.header("Live Trading Dashboard")
    if st.button("Start Trading") and not st.session_state.running:
        st.session_state.running = True
        threading.Thread(target=trading_loop, daemon=True).start()
        st.success("Trading loop started.")
    if st.button("Stop Trading") and st.session_state.running:
        st.session_state.running = False
        st.warning("Trading loop stopped.")

    if st.session_state.trades:
        df = pd.DataFrame(st.session_state.trades)
        st.line_chart(df["price"])
        st.dataframe(df)

# Strategy Config tab
def strategy_tab():
    st.header("Strategy Configuration")
    risk_level = st.slider("Risk Level", 1, 10, 5)
    st.write(f"Selected Risk Level: {risk_level}")
    st.text_input("Strategy Name", "Default Strategy")

# Logs tab
def logs_tab():
    st.header("Execution Logs")
    try:
        with open("sai_trading.log") as f:
            logs = f.read()
        st.text_area("Log Output", logs, height=300)
    except FileNotFoundError:
        st.info("No logs yet.")

# Model Testing tab
def model_tab():
    st.header("Model Testing")
    st.file_uploader("Upload Model File", type=["pkl"])
    st.button("Run Backtest")

# Debug tab
def debug_tab():
    st.header("Debugging Tools")
    st.json({"trades": st.session_state.trades[-5:], "prices": st.session_state.prices[-5:]})

# Main app
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
