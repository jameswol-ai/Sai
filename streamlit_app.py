# streamlit_app.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import threading
import logging
from plugins.exchanges import east_africa
from plugins.prediction import fx_arima, fx_lstm

# Configure logging
logging.basicConfig(filename="logs/app.log", level=logging.INFO)

# Session state init
if "trading_thread" not in st.session_state:
    st.session_state.trading_thread = None
if "fx_data" not in st.session_state:
    st.session_state.fx_data = pd.DataFrame()

# Tabs
tabs = st.tabs(["Dashboard", "Strategy Config", "Logs", "Forecast", "Debug"])

# Dashboard Tab
with tabs[0]:
    st.header("Live FX Dashboard")
    rates = east_africa.get_rates()
    st.write("Base:", rates["base"], "Timestamp:", rates["timestamp"])
    df = pd.DataFrame(rates["rates"].items(), columns=["Currency", "Rate"])
    st.dataframe(df)
    st.line_chart(df.set_index("Currency"))

# Strategy Config Tab
with tabs[1]:
    st.header("Strategy Config")
    base_currency = st.selectbox("Base Currency", ["USD", "EUR", "GBP"])
    st.write("Selected base:", base_currency)

# Logs Tab
with tabs[2]:
    st.header("System Logs")
    with open("logs/app.log") as f:
        st.text(f.read())

# Forecast Tab
with tabs[3]:
    st.header("FX Forecasts")
    currency = st.selectbox("Select Currency", east_africa.CURRENCIES)
    horizon = st.slider("Forecast Horizon (days)", 7, 30, 7)

    # Prepare series
    series = pd.Series([v for v in east_africa.get_rates()["rates"].values()])

    # ARIMA forecast
    arima_preds = fx_arima.forecast(series, steps=horizon)
    st.line_chart(pd.Series(arima_preds, name="ARIMA Forecast"))

    # LSTM forecast
    lstm_model = fx_lstm.train_lstm(series.values, epochs=5)
    lstm_preds = fx_lstm.forecast(lstm_model, series.values, steps=horizon)
    st.line_chart(pd.Series(lstm_preds, name="LSTM Forecast"))

# Debug Tab
with tabs[4]:
    st.header("Debug Tools")
    st.write("Session State:", st.session_state)
