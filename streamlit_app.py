# sai/streamlit_app.py
import streamlit as st
import threading
import time
import logging
import matplotlib.pyplot as plt
import pandas as pd
import random

from sai.bot.main import run_bot, load_model, test_model

# Configure logging
logging.basicConfig(
    filename="sai_app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Initialize session state
if "bot_thread" not in st.session_state:
    st.session_state.bot_thread = None
if "bot_running" not in st.session_state:
    st.session_state.bot_running = False
if "logs" not in st.session_state:
    st.session_state.logs = []
if "rates" not in st.session_state:
    st.session_state.rates = {}

# Helper: threaded bot runner
def start_bot():
    def bot_loop():
        logging.info("Bot started.")
        while st.session_state.bot_running:
            try:
                trade_info = run_bot()
                st.session_state.logs.append(trade_info)
                time.sleep(2)
            except Exception as e:
                logging.error(f"Bot error: {e}")
                st.session_state.logs.append(f"Error: {e}")
                break
        logging.info("Bot stopped.")

    st.session_state.bot_running = True
    st.session_state.bot_thread = threading.Thread(target=bot_loop, daemon=True)
    st.session_state.bot_thread.start()

def stop_bot():
    st.session_state.bot_running = False
    logging.info("Bot stop requested.")

# --- Currency & Forecast Helpers ---
def fetch_currency_data():
    # Dummy currency rates for demo
    currencies = ["USD", "EUR", "GBP", "JPY", "UGX"]
    rates = {cur: round(random.uniform(0.5, 1500), 2) for cur in currencies}
    st.session_state.rates = rates
    return rates

def forecast_rates(rates):
    # Simple forecast: add random drift
    forecast = {cur: val * (1 + random.uniform(-0.05, 0.05)) for cur, val in rates.items()}
    return forecast

# --- Streamlit UI ---
st.set_page_config(page_title="SAI Trading Bot", layout="wide")
st.title("📈 SAI Trading Bot Dashboard")

tabs = st.tabs(["Dashboard", "Strategy Config", "Logs", "Model Testing", "Debug"])

# Dashboard Tab
with tabs[0]:
    st.header("Live Trading Dashboard")
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Start Bot", disabled=st.session_state.bot_running):
            start_bot()
        if st.button("Stop Bot", disabled=not st.session_state.bot_running):
            stop_bot()

    with col2:
        st.write("💱 Currency Rates")
        rates = fetch_currency_data()
        st.table(pd.DataFrame(rates.items(), columns=["Currency", "Rate"]))

        st.write("📊 Forecasted Rates")
        forecast = forecast_rates(rates)
        st.table(pd.DataFrame(forecast.items(), columns=["Currency", "Forecast"]))

        # Graph visualization
        fig, ax = plt.subplots()
        ax.bar(rates.keys(), rates.values(), alpha=0.6, label="Current")
        ax.bar(forecast.keys(), forecast.values(), alpha=0.6, label="Forecast")
        ax.set_ylabel("Rate")
        ax.set_title("Currency Rates vs Forecast")
        ax.legend()
        st.pyplot(fig)

    st.write("Trade Logs (latest 10)")
    st.table(st.session_state.logs[-10:])

# Strategy Config Tab
with tabs[1]:
    st.header("Strategy Configuration")
    risk_level = st.slider("Risk Level", 1, 10, 5)
    st.write(f"Selected Risk Level: {risk_level}")

# Logs Tab
with tabs[2]:
    st.header("Application Logs")
    try:
        with open("sai_app.log", "r") as f:
            log_lines = f.readlines()[-50:]
        st.text("".join(log_lines))
    except FileNotFoundError:
        st.info("No logs yet.")

# Model Testing Tab
with tabs[3]:
    st.header("Model Testing")
    uploaded_model = st.file_uploader("Upload model.pkl", type=["pkl"])
    if uploaded_model:
        model = load_model(uploaded_model)
        st.success("Model loaded successfully.")
        test_results = test_model(model)
        st.write("Test Results:", test_results)

        fig, ax = plt.subplots()
        ax.plot(test_results.get("predictions", []), label="Predictions")
        ax.legend()
        st.pyplot(fig)

# Debug Tab
with tabs[4]:
    st.header("Debug Information")
    st.write("Session State:", st.session_state)
