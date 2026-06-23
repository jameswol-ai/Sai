# streamlit_app.py
import streamlit as st
import pandas as pd
import logging
import plugins/exchanges/east_africa
import plugins/prediction/fx_arima, fx_lstm

logging.basicConfig(filename="logs/app.log", level=logging.INFO)

tabs = st.tabs(["Dashboard", "Strategy Config", "Logs", "Forecast", "Debug"])

# Dashboard
with tabs[0]:
    st.header("Live FX Dashboard")
    rates = east_africa.get_rates()
    df = pd.DataFrame(rates["rates"].items(), columns=["Currency", "Rate"])
    st.write("Base:", rates["base"], "Timestamp:", rates["timestamp"])
    st.dataframe(df)
    st.bar_chart(df.set_index("Currency"))

# Strategy Config
with tabs[1]:
    st.header("Strategy Config")
    base_currency = st.selectbox("Base Currency", ["USD", "EUR", "GBP"])
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

    series = pd.Series(list(east_africa.get_rates()["rates"].values()))

    arima_preds = fx_arima.forecast(series, steps=horizon)
    st.line_chart(pd.Series(arima_preds, name="ARIMA Forecast"))

    lstm_model = fx_lstm.train_lstm(series.values, epochs=5)
    lstm_preds = fx_lstm.forecast(lstm_model, series.values, steps=horizon)
    st.line_chart(pd.Series(lstm_preds, name="LSTM Forecast"))

# Debug
with tabs[4]:
    st.header("Debug Tools")
    st.write("Session State:", st.session_state)
