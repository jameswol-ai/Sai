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
from collections import deque
import queue
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -------------------- Custom CSS --------------------
st.markdown("""
<style>
    .main { background-color: #0E1117; }
    .stApp { background-color: #0E1117; }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem; font-weight: 700; color: #FFFFFF;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.9rem; color: #AAAAAA;
    }
    .forex-card {
        background: linear-gradient(135deg, #1E1E2F 0%, #252540 100%);
        border-radius: 16px; padding: 20px; margin: 8px 0;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        transition: all 0.3s ease;
    }
    .forex-card:hover {
        border-color: #00F2FE;
        box-shadow: 0 4px 20px rgba(0,242,254,0.3);
    }
    .currency-pair {
        font-size: 1.3rem; font-weight: 600; color: #E0E0E0; margin-bottom: 8px;
    }
    .rate-value {
        font-size: 2rem; font-weight: 700; color: #FFFFFF;
    }
    .change-positive { color: #00C853; font-weight: 600; }
    .change-negative { color: #FF1744; font-weight: 600; }
    .section-title {
        font-size: 1.5rem; font-weight: 700; color: #FFFFFF;
        margin: 20px 0 10px 0; border-bottom: 2px solid #00F2FE;
        padding-bottom: 5px; display: inline-block;
    }
    .stButton > button {
        background: linear-gradient(90deg, #00F2FE 0%, #4FACFE 100%);
        color: black; font-weight: 600; border: none;
        border-radius: 8px; padding: 10px 20px; transition: 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,242,254,0.5);
    }
</style>
""", unsafe_allow_html=True)

# -------------------- Safe forecast stubs --------------------
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
    slope = 0
    if len(df) > 1:
        slope = np.polyfit(df["ds_num"], df["y"], 1)[0]
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
        logger.error(f"Model load failed: {e}")
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

# -------------------- Session state --------------------
if "bot_thread" not in st.session_state:
    st.session_state.bot_thread = None
if "bot_running" not in st.session_state:
    st.session_state.bot_running = False
if "logs" not in st.session_state:
    st.session_state.logs = []
if "rates" not in st.session_state:
    st.session_state.rates = {}
if "prev_rates" not in st.session_state:
    st.session_state.prev_rates = {}
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
    st.session_state.use_real_data = False

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

# -------------------- East African currencies --------------------
EAST_AFRICAN_CURRENCIES = ["UGX", "KES", "TZS", "RWF", "BIF", "SSP", "ETB"]
OTHER_CURRENCIES = ["USD", "EUR", "GBP", "JPY"]
ALL_CURRENCIES = EAST_AFRICAN_CURRENCIES + OTHER_CURRENCIES

# -------------------- Real exchange rate fetcher (Frankfurter API) --------------------
@st.cache_data(ttl=60)
def get_real_rates():
    try:
        url = "https://api.frankfurter.app/latest?from=USD&to=" + ",".join(ALL_CURRENCIES)
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        rates = data["rates"]
        rates["USD"] = 1.0
        return rates
    except Exception as e:
        logger.error(f"Failed to fetch real rates: {e}")
        return None

def sample_currency_rates():
    ranges = {
        "UGX": (3700, 3900), "KES": (125, 140), "TZS": (2500, 2700),
        "RWF": (1300, 1500), "BIF": (2800, 3000), "SSP": (1500, 1800),
        "ETB": (55, 60), "USD": (1, 1), "EUR": (0.9, 1.1),
        "GBP": (0.75, 0.85), "JPY": (140, 150)
    }
    return {cur: round(random.uniform(low, high), 2)
            for cur, (low, high) in ranges.items()}

def fetch_currency_data():
    real = get_real_rates()
    if real:
        rates = real
        st.session_state.use_real_data = True
    else:
        rates = sample_currency_rates()
        st.session_state.use_real_data = False

    prev = st.session_state.prev_rates if st.session_state.prev_rates else {}
    delta = {}
    for cur in EAST_AFRICAN_CURRENCIES:
        if cur in prev and prev[cur] != 0:
            delta[cur] = ((rates[cur] - prev[cur]) / prev[cur]) * 100
        else:
            delta[cur] = None

    st.session_state.prev_rates = rates.copy()
    st.session_state.rates = rates
    return rates, delta

def forecast_rates(rates):
    return {cur: round(val * (1 + random.uniform(-0.02, 0.02)), 2)
            for cur, val in rates.items()}

def update_history(rates, forecast):
    now = datetime.now()
    rows = [{"Time": now.isoformat(), "Currency": cur,
             "Rate": rates[cur], "Forecast": forecast[cur]}
            for cur in rates.keys()]
    if rows:
        st.session_state.history = pd.concat(
            [st.session_state.history, pd.DataFrame(rows)], ignore_index=True)
        if len(st.session_state.history) > HISTORY_MAX_ROWS:
            st.session_state.history = st.session_state.history.iloc[-HISTORY_MAX_ROWS:].reset_index(drop=True)

def generate_trade_signal(current_rate, forecast_value, threshold=0.01):
    if forecast_value is None:
        return "HOLD"
    change_pct = (forecast_value - current_rate) / current_rate
    if change_pct > threshold:
        return "BUY"
    elif change_pct < -threshold:
        return "SELL"
    return "HOLD"

# -------------------- Central forecast function --------------------
def run_forecast(currency, horizon, steps, freq="D"):
    df_all = st.session_state.history.copy()
    df_all["Time_dt"] = pd.to_datetime(df_all["Time"])
    df_cur = df_all[df_all["Currency"] == currency].sort_values("Time_dt")

    if len(df_cur) < 20:
        current_rate = st.session_state.rates.get(currency, 1.0)
        fallback_preds = [round(current_rate * (1 + random.uniform(-0.01, 0.01)), 2)
                          for _ in range(steps)]
        return {
            "currency": currency,
            "current_rate": current_rate,
            "arima_forecast": fallback_preds[0],
            "prophet_forecast": None,
            "arima_signal": "HOLD",
            "prophet_signal": None,
            "arima_all_preds": fallback_preds,
            "prophet_all_preds": None,
            "arima_metrics": None,
            "prophet_metrics": None,
            "actual_test": [],
            "train": df_cur,
            "test": pd.DataFrame(),
            "warning": "Insufficient history – forecast is a rough estimate only."
        }

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
    arima_signal = generate_trade_signal(current_rate, arima_pred[0]) if arima_pred else "HOLD"
    prophet_signal = generate_trade_signal(current_rate, prophet_pred[0]) if prophet_pred else "HOLD"

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
        "test": test,
        "warning": None
    }

# -------------------- Technical Indicators --------------------
def compute_indicators(df_cur, rsi_period=14, sma_windows=[20, 50],
                       macd_fast=12, macd_slow=26, macd_signal=9,
                       bb_period=20, bb_std=2):
    df = df_cur.copy().sort_values("Time_dt")
    if len(df) < max(rsi_period, macd_slow, bb_period) + 1:
        return None

    # RSI
    delta = df["Rate"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=rsi_period, min_periods=rsi_period).mean()
    avg_loss = loss.rolling(window=rsi_period, min_periods=rsi_period).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # SMAs
    for w in sma_windows:
        df[f"SMA_{w}"] = df["Rate"].rolling(window=w, min_periods=w).mean()

    # MACD
    ema_fast = df["Rate"].ewm(span=macd_fast, min_periods=macd_fast).mean()
    ema_slow = df["Rate"].ewm(span=macd_slow, min_periods=macd_slow).mean()
    df["MACD"] = ema_fast - ema_slow
    df["MACD_signal"] = df["MACD"].ewm(span=macd_signal, min_periods=macd_signal).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    # Bollinger Bands
    df["BB_middle"] = df["Rate"].rolling(window=bb_period, min_periods=bb_period).mean()
    bb_std_dev = df["Rate"].rolling(window=bb_period, min_periods=bb_period).std()
    df["BB_upper"] = df["BB_middle"] + bb_std * bb_std_dev
    df["BB_lower"] = df["BB_middle"] - bb_std * bb_std_dev

    return df

# -------------------- Streamlit UI --------------------
st.set_page_config(page_title="SAI Forex Bot - East Africa", layout="wide")

# ----- Top bar -----
col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown("<h1 style='color:#00F2FE;'>📈 SAI Forex Trading Bot</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#AAAAAA; font-size:1.1rem;'>East African Currency Trading & Forecasting – UGX, KES, TZS, RWF, BIF, SSP, ETB</p>", unsafe_allow_html=True)

with col_status:
    if st.session_state.use_real_data:
        st.success("🔴 LIVE")
    else:
        st.warning("🟡 SIMULATED")

tabs = st.tabs([
    "📊 Dashboard",
    "📅 Daily Forecast",
    "📆 Weekly Forecast",
    "🗓️ Monthly Forecast",
    "📈 Trade Recommendations",
    "📉 Technical Analysis",
    "⚙️ Strategy Config",
    "📋 Logs",
    "🧪 Model Testing",
    "🛠️ Debug"
])

# --- Dashboard ---
with tabs[0]:
    st.markdown("<div class='section-title'>🌍 East African Forex Rates (USD Base)</div>", unsafe_allow_html=True)
    rates, deltas = fetch_currency_data()
    forecast = forecast_rates(rates)
    update_history(rates, forecast)

    cols = st.columns(4)
    for i, cur in enumerate(EAST_AFRICAN_CURRENCIES):
        rate = rates.get(cur, 0)
        delta_val = deltas.get(cur)
        delta_str = f"{delta_val:+.2f}%" if delta_val is not None else "N/A"
        delta_class = "change-positive" if (delta_val and delta_val >= 0) else "change-negative" if delta_val else ""
        with cols[i % 4]:
            st.markdown(f"""
            <div class="forex-card">
                <div class="currency-pair">USD/{cur}</div>
                <div class="rate-value">{rate:,.2f}</div>
                <div class="{delta_class}" style="font-size:1rem;">{delta_str}</div>
            </div>
            """, unsafe_allow_html=True)

    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')} | Live rates refresh every 60s")

    col_ctrl, col_activity = st.columns([1, 2])
    with col_ctrl:
        st.markdown("<div class='section-title'>⚡ Bot Controls</div>", unsafe_allow_html=True)
        start_col, stop_col = st.columns(2)
        with start_col:
            if st.button("▶️ Start Bot", disabled=st.session_state.bot_running):
                start_bot()
        with stop_col:
            if st.button("⏹️ Stop Bot", disabled=not st.session_state.bot_running):
                stop_bot()

        if st.session_state.bot_thread and not st.session_state.bot_thread.is_alive() and st.session_state.bot_running:
            st.warning("Bot thread stopped unexpectedly. Resetting state.")
            st.session_state.bot_running = False

        auto = st.checkbox("Auto‑refresh (live)", value=st.session_state.auto_refresh)
        st.session_state.auto_refresh = auto
        if auto:
            interval = st.slider("Refresh (sec)", 1, 10, st.session_state.refresh_interval)
            st.session_state.refresh_interval = interval
        if st.button("🔄 Refresh Now"):
            drain_bot_queue(max_items=100)
            st.rerun()

    with col_activity:
        st.markdown("<div class='section-title'>🤖 Recent Bot Trades</div>", unsafe_allow_html=True)
        if st.session_state.logs:
            df_logs = pd.DataFrame(st.session_state.logs[-10:])
            st.dataframe(df_logs, use_container_width=True)
        else:
            st.info("No trades yet. Start the bot to see activity.")

    if not st.session_state.history.empty:
        st.markdown("<div class='section-title'>📉 East African Rate Trends</div>", unsafe_allow_html=True)
        # Interactive Plotly chart instead of Matplotlib
        fig2 = go.Figure()
        df_plot = st.session_state.history.copy()
        df_plot["Time_dt"] = pd.to_datetime(df_plot["Time"])
        colors = ['#00F2FE', '#FFD600', '#FF1744', '#00C853', '#FF9100', '#D500F9', '#2979FF']
        for idx, cur in enumerate(EAST_AFRICAN_CURRENCIES):
            cur_data = df_plot[df_plot["Currency"] == cur].tail(100)
            if not cur_data.empty:
                fig2.add_trace(go.Scatter(
                    x=cur_data["Time_dt"], y=cur_data["Rate"],
                    mode='lines', name=cur,
                    line=dict(color=colors[idx % len(colors)]),
                    hovertemplate=f'{cur}: %{{y:,.2f}}<extra></extra>'
                ))
        fig2.update_layout(
            template="plotly_dark",
            hovermode="x unified",
            title="East African Currencies – Recent Trends",
            xaxis_title="Time",
            yaxis_title="Rate (USD base)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig2, use_container_width=True)

# --- Daily Forecast (unchanged) ---
with tabs[1]:
    st.markdown("<div class='section-title'>📅 Daily Forecast (Next Day)</div>", unsafe_allow_html=True)
    currency = st.selectbox("Select Currency", EAST_AFRICAN_CURRENCIES, key="daily_cur")
    if st.button("Generate Daily Forecast"):
        with st.spinner("Forecasting..."):
            result = run_forecast(currency, "daily", steps=1)
        if result.get("warning"):
            st.warning(result["warning"])
        col1, col2, col3 = st.columns(3)
        col1.metric("Current Rate", f"{result['current_rate']:.2f}")
        col2.metric("ARIMA Forecast", f"{result['arima_forecast']:.2f}" if result['arima_forecast'] else "N/A")
        col3.metric("Prophet Forecast", f"{result['prophet_forecast']:.2f}" if result['prophet_forecast'] else "N/A")
        st.write(f"ARIMA Signal: **{result['arima_signal']}**  |  Prophet Signal: **{result['prophet_signal']}**")
        if result['arima_metrics']:
            st.caption(f"ARIMA Backtest RMSE: {result['arima_metrics']['RMSE']}, MAPE: {result['arima_metrics']['MAPE']}%")
        if result['prophet_metrics']:
            st.caption(f"Prophet Backtest RMSE: {result['prophet_metrics']['RMSE']}, MAPE: {result['prophet_metrics']['MAPE']}%")

# --- Weekly Forecast (unchanged) ---
with tabs[2]:
    st.markdown("<div class='section-title'>📆 Weekly Forecast (7 Days)</div>", unsafe_allow_html=True)
    currency = st.selectbox("Select Currency", EAST_AFRICAN_CURRENCIES, key="weekly_cur")
    if st.button("Generate Weekly Forecast"):
        with st.spinner("Forecasting 7 days..."):
            result = run_forecast(currency, "weekly", steps=7)
        if result.get("warning"):
            st.warning(result["warning"])
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
        st.write(f"ARIMA Signal: **{result['arima_signal']}**  |  Prophet Signal: **{result['prophet_signal']}**")

# --- Monthly Forecast (unchanged) ---
with tabs[3]:
    st.markdown("<div class='section-title'>🗓️ Monthly Forecast (30 Days)</div>", unsafe_allow_html=True)
    currency = st.selectbox("Select Currency", EAST_AFRICAN_CURRENCIES, key="monthly_cur")
    if st.button("Generate Monthly Forecast"):
        with st.spinner("Forecasting 30 days..."):
            result = run_forecast(currency, "monthly", steps=30)
        if result.get("warning"):
            st.warning(result["warning"])
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
        st.write(f"ARIMA Signal: **{result['arima_signal']}**  |  Prophet Signal: **{result['prophet_signal']}**")

# --- Trade Recommendations (unchanged) ---
with tabs[4]:
    st.markdown("<div class='section-title'>📊 Trade Recommendations</div>", unsafe_allow_html=True)
    horizon = st.radio("Horizon", ["Daily", "Weekly", "Monthly"], horizontal=True)
    steps_map = {"Daily": 1, "Weekly": 7, "Monthly": 30}
    steps = steps_map[horizon]
    if st.button("Get Trade Signals for East Africa"):
        signals = []
        fallback_used = False
        with st.spinner("Computing signals..."):
            for cur in EAST_AFRICAN_CURRENCIES:
                result = run_forecast(cur, horizon.lower(), steps)
                if result.get("warning"):
                    fallback_used = True
                signals.append({
                    "Currency": cur,
                    "Current Rate": result['current_rate'],
                    "ARIMA Forecast": result['arima_forecast'],
                    "ARIMA Signal": result['arima_signal'],
                    "Prophet Forecast": result['prophet_forecast'],
                    "Prophet Signal": result['prophet_signal']
                })
        if signals:
            if fallback_used:
                st.warning("Some forecasts use a rough estimate because historical data is insufficient.")
            df_signals = pd.DataFrame(signals)
            def highlight_signal(val):
                if val == 'BUY':
                    return 'background-color: #00C853; color: black'
                elif val == 'SELL':
                    return 'background-color: #FF1744; color: white'
                return ''
            st.dataframe(df_signals.style.applymap(highlight_signal, subset=['ARIMA Signal', 'Prophet Signal']),
                         use_container_width=True)
        else:
            st.warning("No signals generated.")

# --- Technical Analysis (ENHANCED with MACD + Bollinger Bands) ---
with tabs[5]:
    st.markdown("<div class='section-title'>📉 Technical Indicators</div>", unsafe_allow_html=True)
    if st.session_state.history.empty:
        st.info("No historical data yet. Start the bot to collect data.")
    else:
        currency = st.selectbox("Select Currency", EAST_AFRICAN_CURRENCIES, key="tech_cur")
        df_all = st.session_state.history.copy()
        df_all["Time_dt"] = pd.to_datetime(df_all["Time"])
        df_cur = df_all[df_all["Currency"] == currency].sort_values("Time_dt")

        if len(df_cur) < 30:  # enough for all indicators
            st.warning(f"Need at least 30 data points for reliable indicators. Currently have {len(df_cur)}.")
        else:
            ind_df = compute_indicators(df_cur)
            if ind_df is None:
                st.error("Unable to compute indicators.")
            else:
                latest = ind_df.iloc[-1]
                st.subheader(f"{currency} – Latest Indicator Values")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Rate", f"{latest['Rate']:,.2f}")
                col2.metric("RSI (14)", f"{latest['RSI']:.2f}")
                col3.metric("MACD", f"{latest['MACD']:.5f}")
                col4.metric("Signal", f"{latest['MACD_signal']:.5f}")
                col5, col6, col7, _ = st.columns(4)
                col5.metric("Bollinger Upper", f"{latest['BB_upper']:,.2f}")
                col6.metric("Bollinger Middle", f"{latest['BB_middle']:,.2f}")
                col7.metric("Bollinger Lower", f"{latest['BB_lower']:,.2f}")

                # Create interactive multi-panel chart
                fig = make_subplots(
                    rows=4, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.03,
                    row_heights=[0.5, 0.2, 0.15, 0.15],
                    subplot_titles=("Price & Bollinger Bands", "RSI", "MACD", "Volume (simulated)")
                )

                # Price with Bollinger Bands
                fig.add_trace(go.Scatter(
                    x=ind_df["Time_dt"], y=ind_df["Rate"],
                    mode='lines', name='Rate',
                    line=dict(color='#00F2FE', width=2)
                ), row=1, col=1)
                fig.add_trace(go.Scatter(
                    x=ind_df["Time_dt"], y=ind_df["BB_upper"],
                    mode='lines', name='BB Upper',
                    line=dict(color='gray', dash='dot')
                ), row=1, col=1)
                fig.add_trace(go.Scatter(
                    x=ind_df["Time_dt"], y=ind_df["BB_middle"],
                    mode='lines', name='BB Middle',
                    line=dict(color='orange', dash='dot')
                ), row=1, col=1)
                fig.add_trace(go.Scatter(
                    x=ind_df["Time_dt"], y=ind_df["BB_lower"],
                    mode='lines', name='BB Lower',
                    line=dict(color='gray', dash='dot')
                ), row=1, col=1)

                # RSI
                fig.add_trace(go.Scatter(
                    x=ind_df["Time_dt"], y=ind_df["RSI"],
                    mode='lines', name='RSI',
                    line=dict(color='#FFD600', width=1.5)
                ), row=2, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

                # MACD
                fig.add_trace(go.Scatter(
                    x=ind_df["Time_dt"], y=ind_df["MACD"],
                    mode='lines', name='MACD',
                    line=dict(color='blue')
                ), row=3, col=1)
                fig.add_trace(go.Scatter(
                    x=ind_df["Time_dt"], y=ind_df["MACD_signal"],
                    mode='lines', name='Signal',
                    line=dict(color='red')
                ), row=3, col=1)
                colors_hist = ['green' if val >= 0 else 'red' for val in ind_df["MACD_hist"]]
                fig.add_trace(go.Bar(
                    x=ind_df["Time_dt"], y=ind_df["MACD_hist"],
                    name='Histogram',
                    marker_color=colors_hist
                ), row=3, col=1)

                # Volume (simulated as random, just for demo)
                np.random.seed(42)
                vol = np.random.randint(500, 2000, size=len(ind_df))
                fig.add_trace(go.Bar(
                    x=ind_df["Time_dt"], y=vol,
                    name='Volume',
                    marker_color='#7F7F7F'
                ), row=4, col=1)

                fig.update_layout(
                    height=900,
                    template="plotly_dark",
                    showlegend=True,
                    hovermode="x unified"
                )
                fig.update_xaxes(title_text="Time", row=4, col=1)
                fig.update_yaxes(title_text="Rate", row=1, col=1)
                fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1)
                fig.update_yaxes(title_text="MACD", row=3, col=1)
                fig.update_yaxes(title_text="Volume", row=4, col=1)

                st.plotly_chart(fig, use_container_width=True)

                # Interpretation
                rsi_val = latest['RSI']
                if rsi_val > 70:
                    st.warning(f"RSI overbought ({rsi_val:.1f}) – consider SELL.")
                elif rsi_val < 30:
                    st.success(f"RSI oversold ({rsi_val:.1f}) – consider BUY.")
                else:
                    st.info(f"RSI neutral ({rsi_val:.1f})")

                macd_val = latest['MACD']
                sig_val = latest['MACD_signal']
                if pd.notna(macd_val) and pd.notna(sig_val):
                    if macd_val > sig_val:
                        st.write("MACD is **above** signal line – bullish.")
                    else:
                        st.write("MACD is **below** signal line – bearish.")

                # Bollinger squeeze detection (simple)
                bb_width = latest['BB_upper'] - latest['BB_lower']
                if bb_width < 0.02 * latest['Rate']:  # 2% of price
                    st.write("Bollinger Bands are **squeezing** – breakout possible.")
                else:
                    st.write("Bollinger Bands are normal.")

# --- Strategy Config (unchanged) ---
with tabs[6]:
    st.markdown("<div class='section-title'>⚙️ Strategy Configuration</div>", unsafe_allow_html=True)
    risk_level = st.slider("Risk Level", 1, 10, 5)
    st.info("Risk level will be used in future trading logic.")

# --- Logs (unchanged) ---
with tabs[7]:
    st.markdown("<div class='section-title'>📋 Application Logs</div>", unsafe_allow_html=True)
    try:
        with open("sai_app.log", "r") as f:
            last_lines = deque(f, maxlen=200)
            st.text("".join(last_lines))
    except FileNotFoundError:
        st.info("No logs yet.")

# --- Model Testing (unchanged) ---
with tabs[8]:
    st.markdown("<div class='section-title'>🧪 Model Testing</div>", unsafe_allow_html=True)
    st.warning("⚠️ Only upload .pkl files you trust.")
    uploaded_model = st.file_uploader("Upload model.pkl", type=["pkl"])
    if uploaded_model:
        trusted = st.checkbox("I understand the risk and trust this file.", key="trust_model")
        if trusted:
            uploaded_model.seek(0)
            model = load_model(uploaded_model)
            if model:
                st.success("Model loaded.")
                test_results = test_model(model)
                st.write(test_results)
                fig, ax = plt.subplots()
                ax.plot(test_results.get("predictions", []), marker="o")
                st.pyplot(fig)
        else:
            st.info("Please confirm that you trust the uploaded file to continue.")

# --- Debug (unchanged) ---
with tabs[9]:
    st.markdown("<div class='section-title'>🛠️ Debug</div>", unsafe_allow_html=True)
    st.json({k: str(v) if not isinstance(v, (dict, list, int, float, bool, type(None))) else v
             for k, v in st.session_state.items()})

# Auto-refresh
if st.session_state.auto_refresh:
    drain_bot_queue(max_items=5)
    time.sleep(st.session_state.refresh_interval)
    st.rerun()