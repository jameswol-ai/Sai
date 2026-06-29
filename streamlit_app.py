# sai/streamlit_app.py
import streamlit as st
import threading, time, logging, random, pickle, queue, traceback
from logging.handlers import RotatingFileHandler
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime

# --- Forecast plugin imports ---
try:
    from plugins.arima_forecast import fit_arima, forecast_next
except Exception:
    def fit_arima(series, order=(2, 1, 2)): raise RuntimeError("ARIMA plugin not available")
    def forecast_next(model_fit, steps=1): raise RuntimeError("ARIMA plugin not available")

try:
    from plugins.prophet_forecast import fit_prophet, forecast_future
except Exception:
    def fit_prophet(df_rates): raise RuntimeError("Prophet plugin not available")
    def forecast_future(model, periods=1, freq="D"): raise RuntimeError("Prophet plugin not available")

# --- Utility metrics ---
def compute_metrics(actual, predicted):
    actual, predicted = np.array(actual, float), np.array(predicted, float)
    if actual.size == 0 or predicted.size == 0:
        return {"RMSE": None, "MAPE": None}
    n = min(len(actual), len(predicted))
    actual, predicted = actual[-n:], predicted[:n]
    rmse = float(np.sqrt(np.mean((actual - predicted) ** 2)))
    denom = np.where(actual == 0, 1e-8, actual)
    mape = float(np.mean(np.abs((actual - predicted) / denom)) * 100)
    return {"RMSE": round(rmse, 6), "MAPE": round(mape, 4)}

# --- Bot stubs ---
def run_bot():
    return {
        "time": datetime.now().strftime("%H:%M:%S"),
        "trade": random.choice(["BUY","SELL"]),
        "symbol": random.choice(["USD","EUR","GBP","JPY","UGX","KES","TZS","RWF","SSP"]),
        "amount": random.randint(100,5000)
    }

def load_model(file_obj): return pickle.load(file_obj)
def test_model(model): return {"predictions":[1,0,1,1,0],"accuracy":0.8}

# --- Logging ---
logger = logging.getLogger("sai_app")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("sai_app.log", maxBytes=2_000_000, backupCount=3)
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
if not logger.handlers: logger.addHandler(handler)

# --- Session state defaults ---
defaults = {
    "bot_thread":None,"bot_running":False,"logs":[],"rates":{},
    "history":pd.DataFrame(columns=["Time","Currency","Rate","Forecast"]),
    "bot_queue":queue.Queue(),"bot_lock":threading.Lock(),
    "auto_refresh":False,"refresh_interval":3
}
for key, default in defaults.items():
    if key not in st.session_state: st.session_state[key]=default

HISTORY_MAX_ROWS=500

# --- Bot thread ---
def bot_loop(queue_obj, stop_event):
    logger.info("Bot thread started.")
    try:
        while not stop_event.is_set():
            try:
                trade_info=run_bot(); queue_obj.put(trade_info)
            except Exception as e:
                queue_obj.put({"time":datetime.now().strftime("%H:%M:%S"),
                               "error":str(e),"trace":traceback.format_exc()})
                logger.exception("Exception in bot loop"); break
            time.sleep(2)
    finally: logger.info("Bot thread exiting.")

def start_bot():
    if st.session_state.bot_running: return
    stop_event=threading.Event(); st.session_state.stop_event=stop_event
    t=threading.Thread(target=bot_loop,args=(st.session_state.bot_queue,stop_event),daemon=True)
    st.session_state.bot_thread=t; st.session_state.bot_running=True; t.start()

def stop_bot():
    if not st.session_state.bot_running: return
    try: st.session_state.stop_event.set()
    except Exception: logger.exception("Error setting stop event")
    st.session_state.bot_running=False

def drain_bot_queue():
    while not st.session_state.bot_queue.empty():
        try: item=st.session_state.bot_queue.get_nowait()
        except queue.Empty: break
        st.session_state.logs.append(item)
        if isinstance(item,dict) and "trade" in item:
            st.session_state.history=pd.concat([st.session_state.history,
                pd.DataFrame([{"Time":item["time"],"Currency":item["symbol"],
                               "Rate":item["amount"],"Forecast":None}])],ignore_index=True)
        if len(st.session_state.logs)>1000: st.session_state.logs=st.session_state.logs[-1000:]
    if len(st.session_state.history)>HISTORY_MAX_ROWS:
        st.session_state.history=st.session_state.history.iloc[-HISTORY_MAX_ROWS:].reset_index(drop=True)

# --- Currency helpers ---
@st.cache_data(ttl=2)
def sample_currency_rates():
    return {cur:round(random.uniform(0.5,1500),2) for cur in
            ["USD","EUR","GBP","JPY","UGX","KES","TZS","RWF","SSP"]}

def fetch_currency_data():
    st.session_state.rates=sample_currency_rates()
    return st.session_state.rates

def forecast_rates(rates):
    return {cur:round(val*(1+random.uniform(-0.05,0.05)),2) for cur,val in rates.items()}

# --- Streamlit UI ---
st.set_page_config(page_title="SAI Trading Bot", layout="wide")
st.title("📈 SAI Trading Bot Dashboard")

tabs=st.tabs(["Dashboard","Strategy Config","Logs","Model Testing","Debug","Weekly Forecast","Multi-Currency Forecasts"])

# --- Dashboard Tab ---
with tabs[0]:
    st.header("Dashboard")
    st.sidebar.subheader("Controls")
    if st.sidebar.button("Start Bot"): start_bot()
    if st.sidebar.button("Stop Bot"): stop_bot()
    st.sidebar.checkbox("Auto Refresh", key="auto_refresh")
    st.sidebar.slider("Refresh Interval (sec)",1,10,st.session_state.refresh_interval,key="refresh_interval")
    if st.session_state.auto_refresh:
        st.experimental_autorefresh(interval=st.session_state.refresh_interval * 1000)
    drain_bot_queue()
    if not st.session_state.history.empty:
        st.subheader("Recent Trades")
        st.dataframe(st.session_state.history.tail(20))
        st.subheader("Trade Counts by Symbol")
        st.bar_chart(st.session_state.history["Currency"].value_counts())

# --- Weekly Forecast Tab ---
with tabs[5]:
    st.header("Weekly Forecast (East African Currencies)")
    rates=fetch_currency_data(); forecast=forecast_rates(rates)
    rows=[{"Currency":cur,"Rate":rates[cur],"Forecast":forecast[cur]} for cur in rates]
    st.table(pd.DataFrame(rows))

# --- Multi-Currency Forecasts Tab ---
with tabs[6]:
    st.header("Multi-Currency Forecasts (with Confidence Intervals)")
    currencies=list(st.session_state.rates.keys()) or ["USD","EUR","UGX","KES","TZS","RWF","SSP"]
    steps=7; results={}
    for cur in currencies:
        try:
            arima_pred=[round(st.session_state.rates.get(cur,1)*(1+random.uniform(-0.02,0.02)),2) for _ in range(steps)]
            prophet_pred=[round(st.session_state.rates.get(cur,1)*(1+random.uniform(-0.03,0.03)),2) for _ in range(steps)]
            prophet_ci_low=[p*0.95 for p in prophet_pred]; prophet_ci_high=[p*1.05 for p in prophet_pred]
            results[cur]={"ARIMA":arima_pred,"Prophet":prophet_pred,
                          "Prophet_low":prophet_ci_low,"Prophet_high":prophet_ci_high}
        except Exception as e:
            st.error(f"{cur} forecast error: {e}")
            logger.exception("Forecast error for %s",cur)

    if results:
        fig,ax=plt.subplots(figsize=(12,6))
        for cur,preds in results.items():
            ax.plot(range(steps),preds["ARIMA"],marker="o",label=f"{cur} ARIMA")
            ax.plot(range(steps),preds["Prophet"],marker="x",linestyle="--",label=f"{cur} Prophet")
            ax.fill_between(range(steps),preds["Prophet_low"],preds["Prophet_high"],alpha=0.2)
        ax.set_title("7-Day Multi-Currency Forecasts")
        ax.set_xlabel("Days Ahead"); ax.set_ylabel("Rate")
        ax.legend(loc="upper left",bbox_to_anchor=(1.02,1))
        plt.tight_layout(); st.pyplot(fig)

        metrics_rows=[]
        for cur,preds in results.items():
            actual_vals=st.session_state.history[st.session_state.history["Currency"]==cur]["Rate"].values[-steps:]
            if len(actual_vals)>=steps:
                metrics_rows.append({
                    "Currency":cur,
                    "Model":"ARIMA",
                    **compute_metrics(actual_vals,preds["ARIMA"][:steps])
                })
                metrics_rows.append({
                    "Currency":cur,
                    "Model":"Prop
