# streamlit_app.py
import streamlit as st
import pandas as pd
import logging
from datetime import datetime

# Custom plugins
from plugins.exchanges import east_africa
from plugins.prediction import fx_arima, fx_lstm

# Configure logging
logging.basicConfig(filename="logs/app.log", level=logging.INFO)

# Tabs
tabs = st.tabs([
    "Dashboard", "Strategy Config", "Logs",
    "Forecast", "Daily Graph", "Debug"
])

# Dashboard
with tabs[0]:
    st.header("Eastern Africa FX Dashboard")
    try:
        rates = east_africa.get_rates()
        df = pd.DataFrame(rates["rates"].items(), columns=["Currency", "Rate"])
        st.write("Base:", rates["base"], "Timestamp:", rates["timestamp"])
        st.dataframe(df)
        st.bar_chart(df.set_index("Currency"))
    except Exception as e:
        st.error(f"Error fetching rates: {e}")

# Strategy Config
with tabs[1]:
    st.header("Strategy Config")
    base_currency = st.selectbox(
        "Base Currency",
        ["USD", "EUR", "GBP"] + east_africa.CURRENCIES
    )
    st.write("Selected base:", base_currency)

# Logs
with tabs[2]:
    st.header("System Logs")
    try:
        with open("logs/app.log") as f:
            st.text(f.read())
    except FileNotFoundError:
        st.warning("No logs yet.")

# Forecast
with tabs[3]:
    st.header("FX Forecasts")
    currency = st.selectbox("Select Currency", east_africa.CURRENCIES)
    horizon = st.slider("Forecast Horizon (days)", 7, 30, 7)

    history = east_africa.get_daily_history(currency, days=60)
    if history:
        df_hist = pd.DataFrame(history, columns=["Date", "Rate"])
        df_hist["Date"] = pd.to_datetime(df_hist["Date"])
        series = df_hist["Rate"]

        # ARIMA forecast
        try:
            arima_preds = fx_arima.forecast(series, steps=horizon)
            st.line_chart(pd.Series(arima_preds, name="ARIMA Forecast"))
        except Exception as e:
            st.error(f"ARIMA error: {e}")

        # LSTM forecast
        try:
            lstm_model = fx_lstm.train_lstm(series.values, epochs=5)
            lstm_preds = fx_lstm.forecast(lstm_model, series.values, steps=horizon)
            st.line_chart(pd.Series(lstm_preds, name="LSTM Forecast"))
        except Exception as e:
            st.error(f"LSTM error: {e}")
    else:
        st.warning("No historical data available for forecasting.")

# Daily Graph
with tabs[4]:
    st.header("Daily FX Graph")
    currency = st.selectbox("Currency for Daily Graph", east_africa.CURRENCIES)
    history = east_africa.get_daily_history(currency)

    if history:
        df_hist = pd.DataFrame(history, columns=["Date", "Rate"])
        df_hist["Date"] = pd.to_datetime(df_hist["Date"])
        st.line_chart(df_hist.set_index("Date"))
    else:
        st.warning("No daily history available.")

# Debug
with tabs[5]:
    st.header("Debug Tools")
    st.write("Session State:", st.session_state)
