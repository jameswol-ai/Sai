# sai/streamlit_app.py
import streamlit as st
import threading
import time
import logging
from logging.handlers import RotatingFileHandler
import matplotlib.pyplot as plt
import pandas as pd
import random
import pickle
from datetime import datetime, timedelta
import queue
import traceback
import numpy as np
import requests   # For real exchange rates

# -------------------- Safe stubs (real plugins can override) --------------------
def fit_arima(series, order=(2,1,2)):
    return {"last_value": series.iloc[-1], "std": series.std()}

def forecast_next(arima_model, steps=1):
    last = arima_model["last_value"]
    std = arima_model["std"]
    np.random.seed(42)
    return [last + np.random.normal(0, std*0.02) for _ in range(steps)]

def fit_prophet(df_rates):
    df = df_rates.copy()
    df["ds_num"] = (df["ds"] - df["ds"].min()).dt.total_seconds() / 86400
    if len(df) > 1:
        slope = np.polyfit(df["ds_num"], df["y"], 1)[0]
    else:
        slope = 0
    return {"last_date": df["ds"].max(), "slope": slope, "last_y": df["y"].iloc[-1]}

def forecast_future(prophet_model, periods=1, freq="D"):
    last_date = prophet_model["last_date"]
    slope = prophet_model["slope"]
    last_y = prophet_model["last_y"]
    dates = [last_date + timedelta(days=i+1) for i in range(periods)]
    values = [last_y + slope * (i+1) for i in range(periods)]
    return pd.DataFrame({"ds": dates, "yhat": values})

# -------------------- Utility metrics --------------------
def compute_metrics(actual, predicted):
    actual = np.array(actual, dtype=float)
    predicted = np.array(predicted, dtype=float)
    if actual.size == 0 or predicted.size == 0:
        return {"RMSE": None, "MAPE": None}
    n = min(len(actual), len(predicted))
    actual = actual[-n:]
    predicted = predicted[:n]
    rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
    denom = np.where(actual == 0, 1e-8, actual)
    mape = float(np.mean(np.abs((actual - predicted) / denom)) * 100)
    return {"RMSE": round(rmse, 6), "MAPE": round(mape, 4)}

# -------------------- Bot simulation --------------------
def run_bot():
    return {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trade": random.choice(["BUY", "SELL"]),
        "symbol": random.choice(["USD", "EUR", "GBP", "JPY", "UGX", "KES", "TZS", "RWF", "BIF", "SSP", "ETB"]),
        "amount": random.randint(100, 5000)
    }

def load_model(file_obj):
    try:
        return pickle.load(file_obj)
    except Exception as e:
        st.warning(f"Model could not be loaded safely: {e}")
        return None

def test_model(model):
    if model is None:
        return {"predictions": [], "accuracy": 0}
    return {"predictions": [1, 0, 1, 1, 0], "accuracy": 0.8}

# -------------------- Logging --------------------
logger = logging.getLogger("sai_app")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("sai_app.log", maxBytes=2_000_000, backupCount=3)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

# -------------------- Session state init --------------------
if "bot_thread" not in st.session_state:
    st.session_state.bot_thread = None
if "bot_running" not in st.session_state:
    st.session_state.bot_running = False
if "logs" not in st.session_state:
    st.session_state.logs = []
if "rates" not in st.session_state:
    st.session_state.rates = {}
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["Time", "Currency", "Rate", "Forecast"])
if "bot_queue" not in st.session_state:
    st.session_state.bot_queue = queue.Queue()
if "stop_event" not in st.session_state:
    st.session_state.stop_event = threading.Event()
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False
if "refresh_interval" not in st.session_state:
    st.session_state.refresh_interval = 3
if "use_real_data" not in st.session_state:
    st.session_state.use_real_data = False   # will be updated after first fetch

HISTORY_MAX_ROWS = 1000

# -------------------- Bot thread management --------------------
def bot_loop(queue_obj, stop_event):
    logger.info("Bot thread started.")
    while not stop_event.is_set():
        try:
            trade_info = run_bot()
            queue_obj.put(trade_info)
        except Exception as e:
            queue_obj.put({
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error": str(e)
            })
            logger.exception("Bot loop error")
            break
        time.sleep(2)
    logger.info("Bot thread exited.")

def start_bot():
    if st.session_state.bot_running:
        return
    stop_event = threading.Event()
    st.session_state.stop_event = stop_event
    t = threading.Thread(target=bot_loop, args=(st.session_state.bot_queue, stop_event), daemon=True)
    st.session_state.bot_thread = t
    st.session_state.bot_running = True
    t.start()

def stop_bot():
    if st.session_state.bot_running:
        st.session_state.stop_event.set()
        st.session_state.bot_running = False

def drain_bot_queue(max_items=50):
    drained = 0
    while not st.session_state.bot_queue.empty() and drained < max_items:
        try:
            item = st.session_state.bot_queue.get_nowait()
        except queue.Empty:
            break
        st.session_state.logs.append(item)
        drained += 1
    if len(st.session_state.logs) > 1000:
        st.session_state.logs = st.session_state.logs[-1000:]
    return drained

# -------------------- Real exchange rate fetcher (Frankfurter API) --------------------
EAST_AFRICAN_CURRENCIES = ["UGX", "KES", "TZS", "RWF", "BIF", "SSP", "ETB"]
OTHER_CURRENCIES = ["USD", "EUR", "GBP", "JPY"]
ALL_CURRENCIES = EAST_AFRICAN_CURRENCIES + OTHER_CURRENCIES

@st.cache_data(ttl=60)   # cache for 60 seconds to respect API limits
def get_real_rates():
    """Fetch live rates from Frankfurter API (base=USD). Returns dict or None on failure."""
    try:
        # Frankfurter supports many currencies; we request all needed ones.
        url = "https://api.frankfurter.app/latest?from=USD&to=" + ",".join(ALL_CURRENCIES)
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        rates = data["rates"]
        # Add USD itself
        rates["USD"] = 1.0
        return rates
    except Exception as e:
        logger.error(f"Failed to fetch real rates: {e}")
        return None

def sample_currency_rates():
    """Fallback random rates if API fails."""
    rates = {}
    for cur in EAST_AFRICAN_CURRENCIES:
        rates[cur] = round(random.uniform(500, 5000), 2)
    for cur in OTHER_CURRENCIES:
        rates[cur] = round(random.uniform(0.5, 150), 2)
    return rates

def fetch_currency_data():
    """Get current rates: real if available, else simulated."""
    real = get_real_rates()
    if real:
        rates = real
        st.session_state.use_real_data = True
    else:
        rates = sample_currency_rates()
        st.session_state.use_real_data = False
    st.session_state.rates = rates
    return rates

def forecast_rates(rates):
    """Simple short‑term jitter forecast (dashboard visual only)."""
    return {cur: round(val * (1 + random.uniform(-0.02, 0.02)), 2) for cur, val in rates.items()}

def update_history(rates, forecast):
    now = datetime.now()
    rows = []
    for cur in rates.keys():
        rows.append({
            "Time": now.isoformat(),
            "Currency": cur,
            "Rate": rates[cur],
            "Forecast": forecast[cur]
        })
    if rows:
        st.session_state.history = pd.concat(
            [st.session_state.history, pd.DataFrame(rows)], ignore_index=True
        )
        if len(st.session_state.history) > HISTORY_MAX_ROWS:
            st.session_state.history = st.session_state.history.iloc[-HISTORY_MAX_ROWS:].reset_index(drop=True)

def generate_trade_signal(current_rate, forecast_value, threshold=0.01):
    change_pct = (forecast_value - current_rate) / current_rate
    if change_pct > threshold:
        return "BUY"
    elif change_pct < -threshold:
        return "SELL"
    else:
        return "HOLD"

# -------------------- Forecast function (fixed) --------------------
def run_forecast(currency, horizon, steps, freq="D"):
    df_all = st.session_state.history.copy()
    df_all["Time_dt"] = pd.to_datetime(df_all["Time"])
    df_cur = df_all[df_all["Currency"] == currency].sort_values("Time_dt")
    if len(df_cur) < 20:
        return "Not enough data (min 20 points)."

    train = df_cur.iloc[:-steps] if steps < len(df_cur) else df_cur.iloc[:-1]
    test = df_cur.iloc[-steps:] if steps < len(df_cur) else df_cur.iloc[-1:]
    actual_test = test["Rate"].values

    arima_pred = None
    arima_metrics = None
    try:
        arima_model = fit_arima(train["Rate"], order=(2,1,2))
        arima_pred = forecast_next(arima_model, steps=steps)
        arima_metrics = compute_metrics(actual_test, arima_pred[:len(actual_test)])
    except Exception:
        pass

    prophet_pred = None
    prophet_metrics = None
    try:
        df_prophet = pd.DataFrame({"ds": train["Time_dt"], "y": train["Rate"].astype(float)})
        prophet_model = fit_prophet(df_prophet)
        forecast_df = forecast_future(prophet_model, periods=steps, freq=freq)
        prophet_pred = forecast_df["yhat"].tolist()
        prophet_metrics = compute_metrics(actual_test, prophet_pred[:len(actual_test)])
    except Exception:
        pass

    current_rate = df_cur["Rate"].iloc[-1]
    arima_signal = generate_trade_signal(current_rate, arima_pred[0]) if arima_pred else None
    prophet_signal = generate_trade_signal(current_rate, prophet_pred[0]) if prophet_pred else None

    return {
        "currency": currency,
        "current_rate": current_rate,
        "arima_forecast": arima_pred[0] if arima_pred else None,
        "prophet_forecast": prophet_pred[0] if prophet_pred else None,
        "arima_signal": arima_signal,
        "prophet_signal": prophet_signal,
        "arima_all_preds": arima_pred,
        "prophet_all_preds": prophet_pred,
        "arima_metrics": arima_metrics,
        "prophet_metrics": prophet_metrics,
        "actual_test": actual_test,
        "train": train,
        "test": test
    }

# -------------------- Streamlit UI --------------------
st.set_page_config(page_title="SAI Trading Bot - East Africa", layout="wide")
st.title("📈 SAI Trading Bot · East African Currencies")

tabs = st.tabs([
    "Dashboard",
    "Daily Forecast",
    "Weekly Forecast",
    "Monthly Forecast",
    "Trade Recommendations",
    "Strategy Config",
    "Logs",
    "Model Testing",
    "Debug"
])

# Dashboard Tab
with tabs[0]:
    st.header("Live Dashboard")

    # Show data source
    if st.session_state.use_real_data:
        st.success("🌍 Using live exchange rates from Frankfurter API")
    else:
        st.warning("📡 Offline mode – showing simulated rates")

    col1, col2 = st.columns([1, 1])

    with col1:
        start_col, stop_col = st.columns(2)
        with start_col:
            if st.button("Start Bot", disabled=st.session_state.bot_running):
                start_bot()
        with stop_col:
            if st.button("Stop Bot", disabled=not st.session_state.bot_running):
                stop_bot()

        if st.session_state.bot_thread and not st.session_state.bot_thread.is_alive() and st.session_state.bot_running:
            st.warning("Bot thread stopped unexpectedly. Resetting state.")
            st.session_state.bot_running = False

        st.write("**Auto Refresh**")
        auto = st.checkbox("Enable auto refresh", value=st.session_state.auto_refresh)
        st.session_state.auto_refresh = auto
        if auto:
            interval = st.slider("Refresh interval (seconds)", 1, 10, st.session_state.refresh_interval)
            st.session_state.refresh_interval = interval
        if st.button("Refresh Now"):
            drain_bot_queue(max_items=100)
            st.rerun()

    with col2:
        st.write("💱 Current Rates")
        rates = fetch_currency_data()
        df_rates = pd.DataFrame(rates.items(), columns=["Currency", "Rate"])
        st.dataframe(df_rates, use_container_width=True)

        forecast = forecast_rates(rates)
        df_forecast = pd.DataFrame(forecast.items(), columns=["Currency", "Forecast"])
        st.write("📊 Quick Forecast (jitter)")
        st.dataframe(df_forecast, use_container_width=True)

        update_history(rates, forecast)

        fig, ax = plt.subplots(figsize=(8, 4))
        x = list(rates.keys())
        current_vals = list(rates.values())
        forecast_vals = [forecast[k] for k in x]
        width = 0.35
        ax.bar([i - width/2 for i in range(len(x))], current_vals, width=width, alpha=0.7, label="Current")
        ax.bar([i + width/2 for i in range(len(x))], forecast_vals, width=width, alpha=0.7, label="Forecast")
        ax.set_ylabel("Rate")
        ax.set_title("Currency Rates vs Forecast")
        ax.set_xticks(range(len(x)))
        ax.set_xticklabels(x, rotation=45)
        ax.legend()
        st.pyplot(fig)

        if not st.session_state.history.empty:
            st.write("📉 Recent Trend (last 100 points)")
            fig2, ax2 = plt.subplots(figsize=(10, 5))
            df_plot = st.session_state.history.copy()
            df_plot["Time_dt"] = pd.to_datetime(df_plot["Time"])
            for cur in EAST_AFRICAN_CURRENCIES[:6]:
                cur_data = df_plot[df_plot["Currency"] == cur].tail(100)
                if not cur_data.empty:
                    ax2.plot(cur_data["Time_dt"], cur_data["Rate"], label=cur)
            ax2.legend(loc="upper left", bbox_to_anchor=(1,1))
            ax2.set_title("East African Currencies – Rate Trends")
            ax2.set_xlabel("Time")
            ax2.set_ylabel("Rate")
            plt.xticks(rotation=45)
            st.pyplot(fig2)

    st.write("🤖 Bot Activity (latest 10)")
    if st.session_state.logs:
        st.dataframe(pd.DataFrame(st.session_state.logs[-10:]), use_container_width=True)
    else:
        st.info("No bot trades yet.")

# Daily Forecast Tab
with tabs[1]:
    st.header("📅 Daily Forecast (Next Day)")
    currency = st.selectbox("Select Currency", EAST_AFRICAN_CURRENCIES + OTHER_CURRENCIES, key="daily_cur")
    if st.button("Generate Daily Forecast"):
        with st.spinner("Forecasting..."):
            result = run_forecast(currency, "daily", steps=1)
        if isinstance(result, str):
            st.error(result)
        else:
            st.success(f"Forecast for {currency}")
            col1, col2, col3 = st.columns(3)
            col1.metric("Current Rate", f"{result['current_rate']:.2f}")
            col2.metric("ARIMA Forecast", f"{result['arima_forecast']:.2f}" if result['arima_forecast'] else "N/A")
            col3.metric("Prophet Forecast", f"{result['prophet_forecast']:.2f}" if result['prophet_forecast'] else "N/A")
            st.write(f"ARIMA Signal: **{result['arima_signal']}**  |  Prophet Signal: **{result['prophet_signal']}**")
            if result['arima_metrics']:
                st.caption(f"ARIMA Backtest RMSE: {result['arima_metrics']['RMSE']}, MAPE: {result['arima_metrics']['MAPE']}%")
            if result['prophet_metrics']:
                st.caption(f"Prophet Backtest RMSE: {result['prophet_metrics']['RMSE']}, MAPE: {result['prophet_metrics']['MAPE']}%")

# Weekly Forecast Tab
with tabs[2]:
    st.header("📆 Weekly Forecast (7 Days)")
    currency = st.selectbox("Select Currency", EAST_AFRICAN_CURRENCIES + OTHER_CURRENCIES, key="weekly_cur")
    if st.button("Generate Weekly Forecast"):
        with st.spinner("Forecasting 7 days..."):
            result = run_forecast(currency, "weekly", steps=7)
        if isinstance(result, str):
            st.error(result)
        else:
            st.subheader(f"{currency} 7‑Day Outlook")
            fig, ax = plt.subplots()
            days = list(range(1, 8))
            if result['arima_all_preds']:
                ax.plot(days, result['arima_all_preds'], marker='o', label="ARIMA")
            if result['prophet_all_preds']:
                ax.plot(days, result['prophet_all_preds'], marker='x', label="Prophet")
            ax.axhline(y=result['current_rate'], color='gray', linestyle='--', label="Current")
            ax.set_xticks(days)
            ax.set_xlabel("Day")
            ax.set_ylabel("Rate")
            ax.legend()
            st.pyplot(fig)

            col1, col2 = st.columns(2)
            col1.metric("ARIMA Signal", result['arima_signal'])
            col2.metric("Prophet Signal", result['prophet_signal'])
            if result['arima_metrics']:
                st.write(f"ARIMA Backtest: RMSE {result['arima_metrics']['RMSE']}, MAPE {result['arima_metrics']['MAPE']}%")
            if result['prophet_metrics']:
                st.write(f"Prophet Backtest: RMSE {result['prophet_metrics']['RMSE']}, MAPE {result['prophet_metrics']['MAPE']}%")

# Monthly Forecast Tab
with tabs[3]:
    st.header("🗓️ Monthly Forecast (30 Days)")
    currency = st.selectbox("Select Currency", EAST_AFRICAN_CURRENCIES + OTHER_CURRENCIES, key="monthly_cur")
    if st.button("Generate Monthly Forecast"):
        with st.spinner("Forecasting 30 days..."):
            result = run_forecast(currency, "monthly", steps=30)
        if isinstance(result, str):
            st.error(result)
        else:
            st.subheader(f"{currency} 30‑Day Outlook")
            fig, ax = plt.subplots()
            days = list(range(1, 31))
            if result['arima_all_preds']:
                ax.plot(days, result['arima_all_preds'], alpha=0.7, label="ARIMA")
            if result['prophet_all_preds']:
                ax.plot(days, result['prophet_all_preds'], alpha=0.7, label="Prophet")
            ax.axhline(y=result['current_rate'], color='gray', linestyle='--', label="Current")
            ax.set_xlabel("Day")
            ax.set_ylabel("Rate")
            ax.legend()
            st.pyplot(fig)

            col1, col2 = st.columns(2)
            col1.metric("ARIMA Signal", result['arima_signal'])
            col2.metric("Prophet Signal", result['prophet_signal'])
            if result['arima_metrics']:
                st.caption(f"ARIMA Backtest: RMSE {result['arima_metrics']['RMSE']}, MAPE {result['arima_metrics']['MAPE']}%")
            if result['prophet_metrics']:
                st.caption(f"Prophet Backtest: RMSE {result['prophet_metrics']['RMSE']}, MAPE {result['prophet_metrics']['MAPE']}%")

# Trade Recommendations Tab
with tabs[4]:
    st.header("📊 Consolidated Trade Recommendations")
    horizon = st.radio("Select horizon", ["Daily", "Weekly", "Monthly"], horizontal=True)
    steps_map = {"Daily": 1, "Weekly": 7, "Monthly": 30}
    steps = steps_map[horizon]

    if st.button("Get Trade Signals"):
        signals = []
        with st.spinner("Computing signals for all East African currencies..."):
            for cur in EAST_AFRICAN_CURRENCIES:
                result = run_forecast(cur, horizon.lower(), steps)
                if isinstance(result, dict):
                    signals.append({
                        "Currency": cur,
                        "Current Rate": result['current_rate'],
                        "ARIMA Forecast": result['arima_forecast'],
                        "ARIMA Signal": result['arima_signal'],
                        "Prophet Forecast": result['prophet_forecast'],
                        "Prophet Signal": result['prophet_signal']
                    })
                elif isinstance(result, str):
                    st.warning(f"{cur}: {result}")
        if signals:
            df_signals = pd.DataFrame(signals)
            st.dataframe(df_signals.style.applymap(
                lambda x: 'background-color: green' if x == 'BUY' else ('background-color: red' if x == 'SELL' else ''),
                subset=['ARIMA Signal', 'Prophet Signal']
            ), use_container_width=True)
        else:
            st.warning("No signals generated. Ensure sufficient history (≥20 rows per currency).")

# Strategy Config Tab
with tabs[5]:
    st.header("Strategy Configuration")
    risk_level = st.slider("Risk Level", 1, 10, 5)
    st.write(f"Selected Risk Level: {risk_level}")

# Logs Tab
with tabs[6]:
    st.header("Application Logs")
    try:
        with open("sai_app.log", "r") as f:
            log_lines = f.readlines()[-200:]
        st.text("".join(log_lines))
    except FileNotFoundError:
        st.info("No logs yet.")

# Model Testing Tab
with tabs[7]:
    st.header("Model Testing")
    st.markdown("**⚠️ Upload only trusted `.pkl` files.**")
    uploaded_model = st.file_uploader("Upload model.pkl", type=["pkl"])
    if uploaded_model:
        uploaded_model.seek(0)
        model = load_model(uploaded_model)
        if model:
            st.success("Model loaded.")
            test_results = test_model(model)
            st.write(test_results)
            fig, ax = plt.subplots()
            ax.plot(test_results.get("predictions", []), marker="o")
            st.pyplot(fig)

# Debug Tab
with tabs[8]:
    st.header("Debug Information")
    st.write("**Session State Keys:**", list(st.session_state.keys()))
    st.write("**Bot Running:**", st.session_state.bot_running)
    st.write("**Queue Size:**", st.session_state.bot_queue.qsize())
    st.write("**History Rows:**", len(st.session_state.history))
    st.write("**Data Source:**", "Real (Frankfurter)" if st.session_state.use_real_data else "Simulated")
    if st.button("Drain Bot Queue (debug)"):
        drained = drain_bot_queue(max_items=1000)
        st.write(f"Drained {drained} items.")

# Auto-refresh
if st.session_state.auto_refresh:
    drain_bot_queue(max_items=5)
    time.sleep(st.session_state.refresh_interval)
    st.rerun()
